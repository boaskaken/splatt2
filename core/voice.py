"""A single owner thread for speech; no speech engine calls on the UI thread."""
from __future__ import annotations

import logging
import queue
import threading

log = logging.getLogger(__name__)


def shot_message(score, clock, decimal, mode="score_direction"):
    text = f"{score:.1f}" if decimal else str(int(score))
    return text if mode == "score" else f"{text}, {clock} o'clock"


class VoiceFeedback:
    def __init__(self, on_error=None, engine_factory=None):
        self._factory = engine_factory
        self._on_error = on_error or (lambda message: None)
        self._queue = queue.Queue(maxsize=8)
        self._closed = threading.Event()
        self._thread = threading.Thread(target=self._run, name="speech", daemon=True)
        self._thread.start()

    def speak(self, text, settings):
        if self._closed.is_set():
            return False
        try:
            self._queue.put_nowait(("speak", text, dict(settings)))
            return True
        except queue.Full:
            self._on_error("Voice queue is full; announcement skipped.")
            return False

    def list_voices(self, callback):
        if self._closed.is_set():
            callback([])
            return
        try:
            self._queue.put_nowait(("voices", callback, {}))
        except queue.Full:
            callback([])

    def clear(self):
        while True:
            try:
                action, payload, _ = self._queue.get_nowait()
                if action == "voices":
                    payload([])
                self._queue.task_done()
            except queue.Empty:
                return

    def close(self):
        self._closed.set()
        self.clear()
        self._thread.join(timeout=1)

    def _run(self):
        engine = None
        default_voice = None
        while not self._closed.is_set():
            try:
                action, payload, cfg = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                if engine is None:
                    if self._factory is None:
                        import pyttsx3
                        engine = pyttsx3.init()
                    else:
                        engine = self._factory()
                    default_voice = engine.getProperty("voice")
                if action == "voices":
                    payload([(v.id, v.name) for v in engine.getProperty("voices")])
                else:
                    engine.setProperty("voice", cfg.get("voice_id") or default_voice)
                    engine.setProperty("rate", int(cfg.get("voice_rate", 175)))
                    engine.setProperty("volume", float(cfg.get("voice_volume", 1.0)))
                    engine.say(payload)
                    engine.runAndWait()
            except Exception as exc:
                log.exception("Speech failed")
                self._on_error(f"Voice unavailable: {exc}")
                if action == "voices":
                    payload([])
                if engine is not None:
                    try:
                        engine.stop()
                    except Exception:
                        pass
                engine = None
            finally:
                self._queue.task_done()
        if engine is not None:
            try:
                engine.stop()
            except Exception:
                log.exception("Could not stop voice engine")
