# core/io/speech/tts_local.py

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Optional

log = logging.getLogger("tts_local")


class LocalTTS:
    """
    Robust Local TTS wrapper around pyttsx3.

    Key goal:
    - Avoid the "run loop already started" / "speaks once then dies" behavior.
    Approach:
    - Use ONE worker thread + a queue
    - Rebuild the pyttsx3 engine for EACH utterance (most reliable on Windows)
    """

    def __init__(self) -> None:
        self._q: "queue.Queue[Optional[str]]" = queue.Queue()
        self._stop_event = threading.Event()

        self._speaking_lock = threading.Lock()
        self._is_speaking = False

        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

        log.info("Local TTS engine initialized (rebuild-per-utterance worker mode).")

    def _set_speaking(self, val: bool) -> None:
        with self._speaking_lock:
            self._is_speaking = val

    def is_speaking(self) -> bool:
        with self._speaking_lock:
            return self._is_speaking

    def speak(self, text: str) -> None:
        """
        Non-blocking enqueue. Safe to call from any thread.
        """
        if text is None:
            return
        text = str(text).strip()
        if not text:
            return

        log.info(f"TTS enqueue: {text[:80]}{'...' if len(text) > 80 else ''}")
        self._q.put(text)

    def wait_until_done(self, timeout: float | None = None) -> bool:
        """
        Optional helper: wait until queue drains and engine finishes speaking.
        Returns True if done, False if timeout.
        """
        start = time.time()
        while True:
            if self._q.empty() and not self.is_speaking():
                return True
            if timeout is not None and (time.time() - start) > timeout:
                return False
            time.sleep(0.05)

    def stop(self) -> None:
        """
        Stop worker thread cleanly.
        """
        self._stop_event.set()
        self._q.put(None)
        self._worker.join(timeout=2.0)

    def _speak_once(self, text: str) -> None:
        """
        Build a fresh engine and speak once.
        This avoids stuck runloops and device weirdness.
        """
        import pyttsx3  # local import keeps startup light

        engine = None
        self._set_speaking(True)
        try:
            engine = pyttsx3.init()

            # Optional tuning (safe defaults)
            # engine.setProperty("rate", 175)
            # engine.setProperty("volume", 1.0)

            log.info(f"[TTS] start ({len(text)} chars)")
            engine.say(text)
            engine.runAndWait()
            log.info("[TTS] done")

        finally:
            # Always try to stop engine cleanly
            try:
                if engine is not None:
                    engine.stop()
            except Exception:
                pass
            self._set_speaking(False)

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            item = self._q.get()
            if item is None:
                break

            text = (item or "").strip()
            if not text:
                continue

            # Speak with a fresh engine each time
            try:
                self._speak_once(text)
            except Exception as exc:
                log.exception(f"TTS speak error: {exc}")
                # Don't crash the worker; just continue
                continue

        log.info("LocalTTS worker exiting.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    tts = LocalTTS()
    tts.speak("Voice system online. Test one.")
    tts.wait_until_done(timeout=10)

    tts.speak("Test two. If you hear this, the queue is working.")
    tts.wait_until_done(timeout=10)

    tts.stop()
