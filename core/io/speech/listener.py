# core/io/speech/listener.py
"""
Single-chunk microphone listener controlled by EventBus events.

Listens for:
    "voice.listen_toggle"  -> {"listening": True/False}

On listening=True:
    - Records one 5-second audio chunk
    - Saves it to tmp/input.wav
    - Transcribes it with offline STT
    - Publishes: "voice.transcribed" with {"text": "...", "raw_path": ...}

Each F12 press = one listen + one reply.
"""

import os
import threading
import time
import sounddevice as sd
import soundfile as sf

from config.paths import TMP_DIR
from core.logger import get_logger
from core.event_bus import EventBus
from core.io.speech import speech  # STT utilities

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
        state_txt = "ON" if new_state else "OFF"
        log.info(f"VoiceListener toggle received: {state_txt}")

        # We only care about ON to trigger a single listen
        if new_state:
            self.start_listening()

    def start_listening(self):
        if self._listening:
            log.info("VoiceListener: already listening, ignoring new request.")
            return

        log.info("VoiceListener: starting single mic capture")
        self._listening = True
        self._stop_flag.clear()

        self._thread = threading.Thread(target=self._listen_once, daemon=True)
        self._thread.start()

    def _listen_once(self):
        """Record exactly one chunk, transcribe, publish, then stop."""
        try:
            duration = 12  # seconds per chunk (longer so it can catch full phrase)
            samplerate = 44100

            os.makedirs(TMP_DIR, exist_ok=True)
            output_path = os.path.join(TMP_DIR, "input.wav")

            # Record
            log.info(f"Recording mic chunk for {duration} seconds...")
            audio = sd.rec(
                int(duration * samplerate),
                samplerate=samplerate,
                channels=1,
                dtype="float32",
            )
            sd.wait()

            sf.write(output_path, audio, samplerate)
            log.info(f"Saved chunk to: {output_path}")

            # Transcribe
            text = speech.transcribe_audio(output_path)
            log.info(f"Raw STT result: {text!r}")

            payload = {"text": text or "", "raw_path": output_path}
            self.event_bus.publish("voice.transcribed", payload)
            log.info("Published voice.transcribed event")

        except Exception as exc:
            log.exception(f"VoiceListener single capture error: {exc}")
        finally:
            # Mark listener as idle so a new F12 can trigger again
            self._listening = False
            self._stop_flag.set()
            log.info("VoiceListener single capture finished; ready for next F12.")


def start_voice_listener(event_bus: EventBus):
    """Called from core.main to activate listener."""
    return VoiceListener(event_bus)
