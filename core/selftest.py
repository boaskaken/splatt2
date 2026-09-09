"""Offline packaged-app smoke test; no camera, microphone or audible speech."""
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import traceback


def run(report_path, gui=False):
    report = {"ok": False, "checks": [], "hardware_tested": False}
    try:
        with tempfile.TemporaryDirectory(prefix="splatt2-selftest-") as directory:
            os.environ["SPLATT2_USER_DIR"] = directory
            import cv2
            from core.config import DEFAULT_CONFIG, VERSION, save_config, load_config, TARGETS
            from core.marker_sheet import generate_marker_sheet
            from core.tracker import ArucoTracker
            from core.target_renderer import TargetRenderer
            report["version"] = VERSION
            save_config(DEFAULT_CONFIG)
            assert load_config()[0] == DEFAULT_CONFIG
            report["checks"].append("settings round trip")
            for count in (4, 6, 8):
                path = str(Path(directory) / f"sheet{count}.png")
                generate_marker_sheet(path, marker_count=count)
                frame = cv2.resize(cv2.imread(path), (744, 1052))
                result = ArucoTracker().process_frame(frame)
                assert result.markers_found == count and result.quality > .8
            report["checks"].append("4/6/8 marker sheets and tracking")
            for target in TARGETS.values():
                renderer = TargetRenderer(target_cfg=target, canvas_size=(400, 400))
                assert renderer.render(shots=[]).size > 0
            report["checks"].append("all bundled targets render")
            import sounddevice
            driver = "sapi5" if sys.platform == "win32" else "nsss" if sys.platform == "darwin" else "espeak"
            importlib.import_module(f"pyttsx3.drivers.{driver}")
            report["checks"].append("audio and speech driver imports")
            if gui:
                import tkinter as tk
                from ui.app import SettingsDialog
                root = tk.Tk()
                root.withdraw()
                try:
                    dialog = SettingsDialog(root, DEFAULT_CONFIG, save_config)
                    dialog.withdraw()
                    dialog._voice_enabled.set(False)
                    assert dialog._apply()
                    dialog.destroy()
                    assert load_config()[0]["voice_enabled"] is False
                finally:
                    root.destroy()
                report["checks"].append("Tk settings dialog and apply")
            report["ok"] = True
    except Exception:
        report["error"] = traceback.format_exc()
    Path(report_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["ok"] else 1
