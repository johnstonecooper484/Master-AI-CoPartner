"""
speech.py
Audio recording + OFFLINE STT (Whisper) for AI Co-Partner.
"""

import os
import sounddevice as sd
import soundfile as sf
import numpy as np  # for audio arrays

from config.paths import TMP_DIR
from core.logger import get_logger

import whisper  # offline STT

log = get_logger("speech")

# Global cache for the loaded Whisper model
_STT_MODEL = None


# ========== AUDIO RECORDING TEST ==========

def record_test(duration: int = 12, samplerate: int = 44100):
    """Record a short audio clip and save it to tmp/input.wav."""
    log.info(f"Recording audio for {duration} seconds...")

    # Make sure tmp exists
    os.makedirs(TMP_DIR, exist_ok=True)

    output_path = os.path.join(TMP_DIR, "input.wav")

    try:
        audio = sd.rec(
            int(duration * samplerate),
            samplerate=samplerate,
            channels=1,
            dtype="float32",
        )

        sd.wait()  # wait until recording finishes
        sf.write(output_path, audio, samplerate)

        log.info(f"Audio recorded to {output_path}")
        print(f"Audio saved to: {output_path}")

    except Exception as e:
        log.error(f"Audio recording failed: {e}")
        print("Error while recording audio:", e)


# ========== OFFLINE SPEECH-TO-TEXT (STT) WITH WHISPER ==========

def _load_stt_model(model_name: str = "small"):
    """
    Lazily load the Whisper STT model once and cache it globally.

    Common model_name options:
        - "tiny"   (fastest, least accurate)
        - "base"
        - "small"  (good balance on CPU)
        - "medium"
        - "large"  (very heavy)
    """
    global _STT_MODEL

    if _STT_MODEL is not None:
        return _STT_MODEL

    log.info(f"Loading Whisper STT model: {model_name!r} (this may take a moment)...")
    _STT_MODEL = whisper.load_model(model_name)
    log.info("Whisper STT model loaded and ready.")
    return _STT_MODEL


def transcribe_audio(audio_path: str) -> str:
    """
    OFFLINE STT using local Whisper model.

    - Takes a path to a WAV file
    - Loads the audio with soundfile (no ffmpeg)
    - Normalizes the volume
    - Runs Whisper locally (no internet, no API key)
    - Returns the transcribed text as a string
    """
    try:
        if not os.path.exists(audio_path):
            log.error(f"transcribe_audio: file not found: {audio_path}")
            return ""

        # Load audio directly in Python to avoid ffmpeg
        data, samplerate = sf.read(audio_path, dtype="float32")

        # If stereo, convert to mono by averaging channels
        if data.ndim > 1:
            data = data.mean(axis=1)

        # 🔊 Normalize volume so Whisper sees a strong signal
        if data.size:
            max_val = float(np.max(np.abs(data)))
        else:
            max_val = 0.0

        if max_val > 0:
            data = data / max_val

        model = _load_stt_model("small")  # adjust model size here if needed

        log.info(f"Running offline STT on: {audio_path}")
        # Pass the raw audio array instead of file path, and force fp16=False on CPU
        result = model.transcribe(data, language="en", fp16=False)

        text = (result.get("text") or "").strip()
        if not text:
            log.info("Whisper STT returned empty text.")
            return ""

        log.info(f"Whisper STT transcription: {text!r}")
        return text

    except Exception as exc:
        log.exception(f"Offline STT transcription failed: {exc}")
        return ""


# ========== SELF-TEST WHEN RUN DIRECTLY ==========

if __name__ == "__main__":
    print("Recording 12-second test audio...")
    record_test(duration=12)

    print("Transcribing (offline Whisper)...")
    text = transcribe_audio(os.path.join(TMP_DIR, "input.wav"))
    print("Transcription:", text)

    print("Done.")
