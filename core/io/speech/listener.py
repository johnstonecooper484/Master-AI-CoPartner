"""
listener.py
VoiceListener: push-to-talk microphone capture controlled by F12 events.

Event flow:
- hotkeys.py publishes: "voice.listen_toggle"  -> {"listening": True/False}
- this listener subscribes and:
    True  -> start recording (non-blocking)
    False -> stop recording, save wav, run STT, publish "voice.transcribed"

Requires (Windows):
    pip install sounddevice soundfile numpy
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

import numpy as np
import sounddevice as sd
import soundfile as sf

from config.paths import TMP_DIR
from core.logger import get_logger
from core.io.speech import speech  # expects speech.transcribe_audio(path) -> str

log = get_logger("voice_listener")


@dataclass
class _RecConfig:
    samplerate: int = 16000
    channels: int = 1
    dtype: str = "float32"
    device: Optional[int] = None  # None = default input device


class VoiceListener:
    """
    Listens for 'voice.listen_toggle' events and records mic audio while ON.
    On OFF, it finalizes recording, runs STT, and publishes 'voice.transcribed'.
    """

    def __init__(
        self,
        event_bus,
        *,
        samplerate: int = 16000,
        channels: int = 1,
        device: Optional[int] = None,
        output_filename: str = "input.wav",
        min_seconds: float = 0.25,
    ) -> None:
        self.event_bus = event_bus
        self.cfg = _RecConfig(samplerate=samplerate, channels=channels, device=device)
        self.output_path = os.path.join(TMP_DIR, output_filename)
        self.min_seconds = float(min_seconds)

        self._lock = threading.Lock()
        self._is_recording: bool = False
        self._stop_event = threading.Event()
        self._worker: Optional[threading.Thread] = None
        self._frames: List[np.ndarray] = []

        self.event_bus.subscribe("voice.listen_toggle", self._handle_toggle)
        log.info("VoiceListener subscribed to voice.listen_toggle")

    def _handle_toggle(self, data: Dict[str, Any]) -> None:
        listening = bool((data or {}).get("listening", False))
        state_label = "ON" if listening else "OFF"
        log.info(f"VoiceListener toggle received: {state_label}")

        if listening:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self) -> None:
        with self._lock:
            if self._is_recording:
                log.info("VoiceListener: already recording, ignoring start.")
                return
            self._is_recording = True
            self._stop_event.clear()
            self._frames = []

            self._worker = threading.Thread(
                target=self._record_worker,
                name="VoiceListenerRecorder",
                daemon=True,
            )
            self._worker.start()

        log.info("VoiceListener: recording... (F12 OFF to stop)")

    def stop_recording(self) -> None:
        with self._lock:
            if not self._is_recording:
                log.info("VoiceListener: not recording, ignoring stop.")
                return
            self._stop_event.set()

        log.info("VoiceListener: stop requested (will finalize, transcribe, publish).")

        worker = None
        with self._lock:
            worker = self._worker

        if worker and worker.is_alive():
            worker.join(timeout=5.0)

        with self._lock:
            if worker and worker.is_alive():
                log.warning("VoiceListener: recorder thread did not exit in time. Forcing reset.")
                self._is_recording = False
                self._worker = None

    def _record_worker(self) -> None:
        start_time = time.time()

        def callback(indata, frames, time_info, status):
            if status:
                log.debug(f"InputStream status: {status}")

            try:
                self._frames.append(indata.copy())
            except Exception as exc:
                log.exception(f"VoiceListener: failed to append audio frame: {exc}")

            if self._stop_event.is_set():
                raise sd.CallbackStop()

        try:
            os.makedirs(TMP_DIR, exist_ok=True)

            with sd.InputStream(
                samplerate=self.cfg.samplerate,
                channels=self.cfg.channels,
                dtype=self.cfg.dtype,
                device=self.cfg.device,
                callback=callback,
            ):
                while not self._stop_event.is_set():
                    time.sleep(0.05)

        except Exception as exc:
            log.exception(f"VoiceListener: recording crashed: {exc}")

        try:
            duration = time.time() - start_time
            audio = self._finalize_audio(duration)
            if audio is None:
                return

            sf.write(self.output_path, audio, self.cfg.samplerate)
            log.info(f"Saved chunk to: {self.output_path}")

            text = speech.transcribe_audio(self.output_path)
            raw_text = (text or "").strip()
            log.info(f'Raw STT result: "{raw_text}"')

            cleaned = self._clean_transcript(raw_text)
            log.info(f'Cleaned STT result: "{cleaned}"')

            if cleaned:
                self.event_bus.publish(
                    "voice.transcribed",
                    {"text": cleaned, "raw_path": self.output_path},
                )
            else:
                log.info("VoiceListener: empty transcript, nothing to publish.")

        finally:
            with self._lock:
                self._is_recording = False
                self._worker = None
                self._stop_event.clear()
                self._frames = []

    def _finalize_audio(self, duration: float) -> Optional[np.ndarray]:
        if duration < self.min_seconds:
            log.info(f"VoiceListener: recording too short ({duration:.2f}s). Ignoring.")
            return None

        if not self._frames:
            log.warning("VoiceListener: no audio frames captured.")
            return None

        audio = np.concatenate(self._frames, axis=0)

        if audio.ndim == 2 and audio.shape[1] == 1:
            audio = audio[:, 0]

        if float(np.max(np.abs(audio))) < 1e-4:
            log.info("VoiceListener: audio is nearly silent. Ignoring.")
            return None

        return audio

    @staticmethod
    def _clean_transcript(text: str) -> str:
        t = (text or "").strip()
        lowered = t.lower()

        for phrase in ["stop listening", "start listening"]:
            if lowered.endswith(phrase):
                t = t[: -len(phrase)].strip(" ,.-!?\n\t")
                lowered = t.lower()

        return t


def start_voice_listener(event_bus) -> VoiceListener:
    """
    Entry point used by core.main:
        from core.io.speech.listener import start_voice_listener
    """
    return VoiceListener(event_bus)
