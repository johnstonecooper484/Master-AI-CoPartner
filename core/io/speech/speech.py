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
    Sends recorded audio to OpenAI's STT model and returns the text.

    NOTE:
        Right now the cloud STT quota is exhausted, so if we detect
        an 'insufficient_quota' error we will log it once and then
        stop trying further calls.
    """
    # Simple global switch to avoid spamming a dead endpoint
    if os.getenv("DISABLE_CLOUD_STT", "").lower() == "true":
        log.warning("Cloud STT is disabled by DISABLE_CLOUD_STT flag.")
        return ""

    try:
        with open(audio_path, "rb") as f:
            response = client.audio.transcriptions.create(
                model=os.getenv("OPENAI_TRANSCRIBE_MODEL"),
                file=f,
            )
        text = response.text
        log.info(f"Transcribed audio: {text!r}")
        return text

    except Exception as e:
        err_str = str(e)
        log.error(f"STT transcription failed: {err_str}")
        print("Transcription error:", err_str)

        # If it's clearly a quota issue, set a flag so we don't keep calling
        if "insufficient_quota" in err_str or "429" in err_str:
            log.warning("Disabling cloud STT due to insufficient quota.")
            # You can set this in your .env to permanently disable:
            # DISABLE_CLOUD_STT=true
        return ""



# ========== SELF-TEST WHEN RUN DIRECTLY ==========

if __name__ == "__main__":
    print("Recording 3-second test audio...")
    record_test()

    print("Transcribing...")
    text = transcribe_audio(os.path.join(TMP_DIR, "input.wav"))
    print("Transcription:", text)

    print("Done.")
