"""
speech.py
Audio recording + OpenAI STT for AI Co-Partner.
"""

import os
import sounddevice as sd
import soundfile as sf

from config.paths import TMP_DIR
from core.logger import get_logger

log = get_logger("speech")

# Track whether we've already warned about STT being disabled
_STT_DISABLED_LOGGED = False

# ========== AUDIO RECORDING TEST ==========

def record_test(duration: int = 3, samplerate: int = 44100):
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
            dtype='float32'
        )

        sd.wait()  # wait until recording finishes
        sf.write(output_path, audio, samplerate)

        log.info(f"Audio recorded to {output_path}")
        print(f"Audio saved to: {output_path}")

    except Exception as e:
        log.error(f"Audio recording failed: {e}")
        print("Error while recording audio:", e)


# ========== OPENAI SPEECH-TO-TEXT (STT) ==========

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # load key from .env
client = OpenAI()

def transcribe_audio(audio_path: str) -> str:
    """
    Offline placeholder for speech-to-text.

    Important:
        - This function does NOT call any cloud APIs.
        - It exists so the rest of the voice pipeline can run
          (recording, F12 toggle, etc.) without errors.
        - Later, we will replace the body with an OFFLINE STT engine
          (e.g., local Whisper) so your AI can understand speech
          without touching the internet.
    """
    global _STT_DISABLED_LOGGED

    # Log once per run so you know what's happening, but don't spam.
    if not _STT_DISABLED_LOGGED:
        log.info(
            "transcribe_audio called, but STT is currently offline-only. "
            "No cloud requests will be made until an offline STT engine is configured."
        )
        _STT_DISABLED_LOGGED = True

    # For now, we return an empty string to indicate "no transcription".
    return ""




# ========== SELF-TEST WHEN RUN DIRECTLY ==========

if __name__ == "__main__":
    print("Recording 3-second test audio...")
    record_test()

    print("Transcribing...")
    text = transcribe_audio(os.path.join(TMP_DIR, "input.wav"))
    print("Transcription:", text)

    print("Done.")
