"""
speech.py
Audio recording + OFFLINE STT (faster-whisper) for AI Co-Partner.
"""

import os
import sounddevice as sd
import soundfile as sf
import numpy as np

from config.paths import TMP_DIR
from core.logger import get_logger
from core.io.speech.stt_faster_whisper import transcribe_wav

log = get_logger("speech")


# ========== AUDIO RECORDING TEST ==========

def record_test(duration: int = 12, samplerate: int = 44100):
    """Record a short audio clip and save it to tmp/input.wav."""
    log.info(f"Recording audio for {duration} seconds...")

    os.makedirs(TMP_DIR, exist_ok=True)
    output_path = os.path.join(TMP_DIR, "input.wav")

    try:
        audio = sd.rec(
            int(duration * samplerate),
            samplerate=samplerate,
            channels=1,
            dtype="float32",
        )
        sd.wait()
        sf.write(output_path, audio, samplerate)

        log.info(f"Audio recorded to {output_path}")
        print(f"Audio saved to: {output_path}")

    except Exception as e:
        log.error(f"Audio recording failed: {e}")
        print("Error while recording audio:", e)


# ========== OFFLINE SPEECH-TO-TEXT (STT) ==========

def transcribe_audio(audio_path: str) -> str:
    """
    OFFLINE STT using faster-whisper.

    - Takes a path to a WAV file
    - Uses faster-whisper (offline)
    - Returns transcribed text
    """
    if not os.path.exists(audio_path):
        log.error(f"transcribe_audio: file not found: {audio_path}")
        return ""

    log.info(f"Running offline STT (faster-whisper) on: {audio_path}")

    text = transcribe_wav(audio_path, language="en")
    text = (text or "").strip()

    if text:
        log.info(f"STT transcription: {text!r}")
    else:
        log.info("STT returned empty text (no speech detected).")

    return text


# ========== SELF-TEST ==========

if __name__ == "__main__":
    print("Recording 12-second test audio...")
    record_test(duration=12)

    print("Transcribing (offline faster-whisper)...")
    text = transcribe_audio(os.path.join(TMP_DIR, "input.wav"))
    print("Transcription:", text)

    print("Done.")
