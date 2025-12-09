# core/io/speech/listener.py
"""
Continuous microphone listener controlled by EventBus events.

Listens for:
    "voice.listen_toggle"  -> {"listening": True/False}

When ON:
    - Records a short 2-second audio chunk (for now)
    - Saves it to tmp/input.wav
    - Transcribes it
    - Publishes: "voice.transcribed" event with {"text": "..."}
"""

import os
import threading
import time
import sounddevice as sd
import soundfile as sf

from config.paths import TMP_DIR
from core.logger import get_logger
from core.event_bus import EventBus
from core.io.speech import speech  # imports your record + transcribe utilities

log = get_logger("voice_listener")


class VoiceListener:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._listening = False
        self._thread = None
        self._stop_flag = threading.Event()

        # Subscribe to F12 toggle events
        self.event_bus.subscribe("voice.listen_toggle", self._handle_toggle)
        log.info("VoiceListener subscribed to voice.listen_toggle")

    def _handle_toggle(self, data):
        """Called whenever F12 toggles listening state."""
        new_state = data.get("listening", False)
        log.info(f"VoiceListener toggle received: {new_state}")

        if new_state and not self._listening:
            self.start_listening()
        elif not new_state and self._listening:
            self.stop_listening()

    def start_listening(self):
        if self._listening:
            return

        log.info("VoiceListener: starting mic loop")
        self._listening = True
        self._stop_flag.clear()

        self._thread = threading.Thread(
            target=self._listen_loop, daemon=True
        )
        self._thread.start()

    def stop_listening(self):
        if not self._listening:
            return

        log.info("VoiceListener: stopping mic loop")
        self._listening = False
        self._stop_flag.set()

    def _listen_loop(self):
        """Records repeatedly until stopped."""
        while not self._stop_flag.is_set():
            try:
                duration = 2  # seconds per chunk for now
                samplerate = 44100

                os.makedirs(TMP_DIR, exist_ok=True)
                output_path = os.path.join(TMP_DIR, "input.wav")

                log.info("Recording mic chunk...")
                audio = sd.rec(
                    int(duration * samplerate),
                    samplerate=samplerate,
                    channels=1,
                    dtype="float32",
                )
                sd.wait()

                sf.write(output_path, audio, samplerate)
                log.info(f"Saved chunk to: {output_path}")

                # STT
                text = speech.transcribe_audio(output_path)
                if text:
                    log.info(f"Transcribed: {text!r}")
                    self.event_bus.publish("voice.transcribed", {"text": text})

            except Exception as exc:
                log.exception(f"VoiceListener mic loop error: {exc}")

            time.sleep(0.2)  # tiny pause

        log.info("VoiceListener mic loop exited")


def start_voice_listener(event_bus: EventBus):
    """Called from core.main to activate listener."""
    listener = VoiceListener(event_bus)
    return listener
