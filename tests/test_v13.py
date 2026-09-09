"""Hardware-independent regression tests; GUI cases require working Tcl/Tk."""
import json
import os
import queue
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

_data = tempfile.TemporaryDirectory(prefix="splatt2-tests-")
os.environ["SPLATT2_USER_DIR"] = _data.name

import cv2
import numpy as np
from core import config
from core.tracker import ArucoTracker, _build_board_corners
from core.marker_sheet import generate_marker_sheet
from core.voice import VoiceFeedback, shot_message


class ConfigTests(unittest.TestCase):
    def test_collect_empty_text_and_device_index(self):
        from ui.app import SettingsDialog
        fake = SimpleNamespace(cfg=config.DEFAULT_CONFIG.copy())
        for key, value in (("save_directory", ""), ("audio_device_index", "3"),
                           ("voice_rate", "200"), ("session_name", "True")):
            setattr(fake, "_v_" + key, Mock(get=Mock(return_value=value)))
        SettingsDialog._collect(fake)
        self.assertEqual(fake.cfg["save_directory"], "")
        self.assertEqual(fake.cfg["audio_device_index"], 3)
        self.assertEqual(fake.cfg["session_name"], "True")
        self.assertEqual(fake.cfg["voice_rate"], 200)
        self.assertFalse(config.validate_config(fake.cfg))

    def test_round_trip_and_migration(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(config, "CONFIG_FILE", str(Path(folder)/"config.json")):
            cfg = config.DEFAULT_CONFIG.copy()
            cfg.update(voice_enabled=False, voice_rate=210, voice_id="test voice", aruco_marker_count="Auto")
            config.save_config(cfg)
            self.assertEqual(config.load_config(), (cfg, False))
            Path(config.CONFIG_FILE).write_text(json.dumps({"target_black_rings": 3}), encoding="utf-8")
            self.assertEqual(config.load_config()[0]["target_inner_rings"], 3)

    def test_legacy_null_directory_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(config, "CONFIG_FILE", str(Path(folder)/"config.json")):
            Path(config.CONFIG_FILE).write_text('{"save_directory": null}', encoding="utf-8")
            cfg, first = config.load_config()
            self.assertEqual(cfg["save_directory"], "")
            self.assertFalse(first)
            self.assertFalse(config.CONFIG_WARNINGS)

    def test_failed_replace_preserves_original(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(config, "CONFIG_FILE", str(Path(folder)/"config.json")):
            config.save_config(config.DEFAULT_CONFIG)
            original = Path(config.CONFIG_FILE).read_bytes()
            with patch("core.config.os.replace", side_effect=PermissionError("locked")):
                with self.assertRaises(PermissionError):
                    config.save_config(dict(config.DEFAULT_CONFIG, voice_enabled=False))
            self.assertEqual(Path(config.CONFIG_FILE).read_bytes(), original)
            self.assertEqual(len(list(Path(folder).iterdir())), 1)

    def test_validation_and_invalid_load(self):
        self.assertFalse(config.validate_config(config.DEFAULT_CONFIG))
        bad = dict(config.DEFAULT_CONFIG, voice_rate=-1, voice_enabled="False",
                   smooth_window=2, camera_zoom=float("nan"), colour_target_inner="red")
        self.assertTrue(set(("voice_rate", "voice_enabled", "smooth_window", "camera_zoom", "colour_target_inner")) <= config.validate_config(bad).keys())
        with tempfile.TemporaryDirectory() as folder, patch.object(config, "CONFIG_FILE", str(Path(folder)/"config.json")):
            Path(config.CONFIG_FILE).write_text(json.dumps(bad), encoding="utf-8")
            loaded, _ = config.load_config()
            self.assertFalse(config.validate_config(loaded))
            self.assertTrue(config.CONFIG_WARNINGS)
            Path(config.CONFIG_FILE).write_text("[]", encoding="utf-8")
            self.assertEqual(config.load_config()[0], config.DEFAULT_CONFIG)


class TrackingTests(unittest.TestCase):
    def test_reset_for_smaller_sheet(self):
        tracker = ArucoTracker()
        self.detect(tracker, list(range(8)))
        tracker.reset()
        result = self.detect(tracker, [0, 1, 2, 3])
        self.assertEqual(result.markers_expected, 4)
        self.assertGreater(result.quality, .9)

    def test_printed_sheets(self):
        with tempfile.TemporaryDirectory() as folder:
            for count in (4, 6, 8):
                path = str(Path(folder)/f"sheet{count}.png")
                generate_marker_sheet(path, marker_count=count)
                frame = cv2.resize(cv2.imread(path), (744, 1052))
                t = ArucoTracker(marker_count="Auto")
                result = t.process_frame(frame)
                self.assertEqual(result.markers_found, count)
                self.assertEqual(result.markers_expected, count)
                self.assertGreater(result.quality, .85)
                self.assertLess(abs(result.aim_mm[0]), 1)
                self.assertLess(abs(result.aim_mm[1]), 1)

    def detect(self, tracker, ids, noise=0):
        board = _build_board_corners(210, 297, 40, 8)
        rng = np.random.default_rng(3)
        corners = [(board.get(i, board[0]) + rng.normal(0, noise, (4, 2))).astype(np.float32).reshape(1, 4, 2) for i in ids]
        tracker.detector = Mock()
        tracker.detector.detectMarkers.return_value = (corners, np.array(ids, dtype=np.int32).reshape(-1, 1), [])
        return tracker.process_frame(np.zeros((300, 210, 3), dtype=np.uint8))

    def test_occlusion_unknown_and_duplicate_ids(self):
        t = ArucoTracker()
        self.detect(t, list(range(8)))
        r = self.detect(t, [0, 1, 2, 3, 49])
        self.assertEqual((r.markers_found, r.markers_expected), (4, 8))
        self.assertLessEqual(r.quality, .5)
        r = self.detect(t, [0, 0, 1, 49])
        self.assertEqual(r.markers_found, 1)
        t.detector.detectMarkers.return_value = ([], None, [])
        previous = r.quality
        for age in range(1, 7):
            r = t.process_frame(np.zeros((300, 210, 3), dtype=np.uint8))
            self.assertLessEqual(r.quality, previous)
            previous = r.quality
        self.assertIsNone(r.aim_mm)

    def test_spread_and_fit_affect_quality(self):
        corners = self.detect(ArucoTracker(), [0, 1, 2, 3])
        clustered = self.detect(ArucoTracker(), [0, 1])
        noisy = self.detect(ArucoTracker(), [0, 1, 2, 3], noise=2)
        self.assertGreater(corners.quality, clustered.quality)
        self.assertGreater(corners.quality, noisy.quality)


class VoiceTests(unittest.TestCase):
    def test_clear_discards_waiting_speech(self):
        started, release = threading.Event(), threading.Event()
        engine = Mock()
        def run():
            started.set()
            release.wait(2)
        engine.runAndWait.side_effect = run
        voice = VoiceFeedback(engine_factory=lambda: engine)
        try:
            voice.speak("first", {})
            self.assertTrue(started.wait(2))
            voice.speak("cancelled", {})
            voice.clear()
            release.set()
            self.wait_empty(voice)
            engine.say.assert_called_once_with("first")
        finally:
            release.set()
            voice.close()

    def test_serial_engine_and_options(self):
        calls = []
        class Engine:
            def getProperty(self, name):
                return "default"
            def setProperty(self, key, value):
                calls.append((threading.get_ident(), key, value))
            def say(self, text):
                calls.append((threading.get_ident(), "say", text))
            def runAndWait(self):
                time.sleep(.01)
            def stop(self):
                pass
        factory = Mock(side_effect=Engine)
        errors = []
        voice = VoiceFeedback(errors.append, factory)
        try:
            for n in range(3):
                voice.speak(str(n), dict(voice_rate=200, voice_volume=.5, voice_id="chosen"))
            self.wait_empty(voice)
        finally:
            voice.close()
        self.assertEqual(factory.call_count, 1)
        self.assertEqual([x[2] for x in calls if x[1] == "say"], ["0", "1", "2"])
        self.assertEqual(len(set(x[0] for x in calls)), 1)
        self.assertNotEqual(calls[0][0], threading.get_ident())
        self.assertFalse(errors)

    def wait_empty(self, voice):
        deadline = time.monotonic() + 3
        while voice._queue.unfinished_tasks and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertEqual(voice._queue.unfinished_tasks, 0)

    def test_failure_and_format(self):
        errors = []
        voice = VoiceFeedback(errors.append, Mock(side_effect=RuntimeError("missing engine")))
        try:
            voice.speak("test", {})
            self.wait_empty(voice)
            self.assertIn("missing engine", errors[0])
        finally:
            voice.close()
        self.assertFalse(voice.speak("closed", {}))
        self.assertEqual(shot_message(9.5, 3, False, "score"), "9")
        self.assertEqual(shot_message(9.5, 3, True), "9.5, 3 o'clock")


class GuiTests(unittest.TestCase):
    def test_main_window_and_simulated_shot(self):
        import tkinter as tk
        from ui.app import SplattApp
        try:
            probe = tk.Tk()
            probe.withdraw()
            probe.destroy()
        except tk.TclError as exc:
            if os.environ.get("SPLATT2_REQUIRE_GUI") == "1":
                raise
            self.skipTest(str(exc))
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(config, "CONFIG_FILE", str(Path(folder)/"config.json")), \
             patch("ui.app.VoiceFeedback"), \
             patch.object(SplattApp, "_scan_cameras"), \
             patch.object(SplattApp, "_show_first_run_wizard"):
            app = SplattApp()
            errors = []
            app.root.report_callback_exception = lambda *args: errors.append(args)
            app.root.withdraw()
            try:
                self.assertIn("1.3 Community", app.root.title())
                app.root.update_idletasks()
                draft = dict(app.cfg, voice_rate=220, save_directory=folder)
                app._apply_settings(draft)
                app._series_started = True
                app._register_shot((0, 0))
                app.root.update()
                self.assertEqual(len(app.session.shots), 1)
                app.voice.speak.assert_called_once()
                self.assertEqual(config.load_config()[0]["voice_rate"], 220)
                self.assertFalse(errors)
            finally:
                app._on_close()

    def test_settings_apply_reopen(self):
        import tkinter as tk
        from ui.app import SettingsDialog
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            if os.environ.get("SPLATT2_REQUIRE_GUI") == "1":
                raise
            self.skipTest(str(exc))
        root.withdraw()
        try:
            with tempfile.TemporaryDirectory() as folder, patch.object(config, "CONFIG_FILE", str(Path(folder)/"config.json")):
                cfg = config.DEFAULT_CONFIG.copy()
                dialog = SettingsDialog(root, cfg, config.save_config, Mock())
                dialog.withdraw()
                dialog._voice_enabled.set(False)
                dialog._v_voice_rate.set("220")
                self.assertTrue(dialog._apply())
                dialog.destroy()
                saved, _ = config.load_config()
                dialog = SettingsDialog(root, saved, config.save_config, Mock())
                dialog.withdraw()
                self.assertFalse(dialog._voice_enabled.get())
                self.assertEqual(dialog._v_voice_rate.get(), "220")
                dialog._v_voice_rate.set("wrong")
                with patch("ui.app.messagebox.showerror"):
                    self.assertFalse(dialog._apply())
                self.assertEqual(config.load_config()[0]["voice_rate"], 220)
                dialog.destroy()
        finally:
            root.destroy()


class AudioTests(unittest.TestCase):
    def test_failed_start_cleans_stream_and_reports(self):
        from core.audio import AudioDetector
        stream = Mock()
        stream.start.side_effect = RuntimeError("device disconnected")
        with patch("core.audio.SD_AVAILABLE", True), patch("core.audio.sd.InputStream", return_value=stream):
            detector = AudioDetector()
            detector.start()
            self.assertFalse(detector._running)
            self.assertIn("device disconnected", detector.last_error)
            self.assertIsNone(detector._stream)
            stream.close.assert_called_once()

    def test_transient_and_pause(self):
        from core.audio import AudioDetector
        callback = Mock()
        detector = AudioDetector(threshold=.1, transient_ratio=2, on_shot=callback)
        pulse = np.zeros((512, 1), np.float32)
        pulse[0, 0] = .9
        detector._audio_callback(pulse, 512, None, None)
        callback.assert_called_once()

        detector.pause(True)
        detector._last_trigger_time = 0
        detector._audio_callback(pulse, 512, None, None)
        callback.assert_called_once()


class AppIntegrationTests(unittest.TestCase):
    def test_settings_save_failure_leaves_runtime_unchanged(self):
        from ui.app import SplattApp
        fake = SimpleNamespace(cfg=config.DEFAULT_CONFIG.copy(),
            _CAM_RESTART_KEYS=SplattApp._CAM_RESTART_KEYS,
            _TRACKER_REBUILD_KEYS=SplattApp._TRACKER_REBUILD_KEYS)
        draft = dict(fake.cfg, voice_rate=220)
        with patch("ui.app.save_config", side_effect=PermissionError("read only")):
            with self.assertRaises(PermissionError):
                SplattApp._apply_settings(fake, draft)
        self.assertEqual(fake.cfg["voice_rate"], 175)

    def test_camera_failure_is_queued_for_ui(self):
        from ui.app import SplattApp
        fake = SimpleNamespace(_closing=False, _loop_done=threading.Event(),
            _open_capture=Mock(side_effect=RuntimeError("driver unavailable")),
            _notifications=queue.Queue(), _camera_results=queue.Queue())
        fake._loop_done.set()
        SplattApp._open_camera_in_background(fake, 2)
        self.assertEqual(fake._camera_results.get_nowait(), (2, None))
        self.assertIn("driver unavailable", fake._notifications.get_nowait())

    def test_registered_shots_use_queue_and_ignored_misses_do_not(self):
        from ui.app import SplattApp
        from core.session import Session
        fake = SimpleNamespace(cfg=dict(config.DEFAULT_CONFIG, voice_mode="score"),
            _series_started=True, _decimal_scoring=True, _scoring_radius_mm=lambda:25,
            target_cfg={}, session=Session(scoring_radius_mm=25), voice=Mock(), root=Mock())
        SplattApp._register_shot(fake, (0, 0))
        self.assertEqual(len(fake.session.shots), 1)
        fake.voice.speak.assert_called_once()
        self.assertNotIn("o'clock", fake.voice.speak.call_args.args[0])
        fake.cfg["voice_enabled"] = False
        SplattApp._register_shot(fake, (0, 0))
        self.assertEqual(len(fake.session.shots), 2)
        fake.voice.speak.assert_called_once()
        fake.cfg.update(voice_enabled=True, ignore_misses=True)
        fake.session._writer = Mock(is_open=True)
        SplattApp._register_shot(fake, (26, 0))
        self.assertEqual(len(fake.session.shots), 2)
        fake.voice.speak.assert_called_once()
        fake.session._writer.write_shot.assert_not_called()


if __name__ == "__main__":
    unittest.main()
