from core.io.speech.speech import transcribe_audio
from config.paths import TMP_DIR
import os

audio_path = os.path.join(TMP_DIR, "input.wav")
print("Transcribing:", audio_path)

text = transcribe_audio(audio_path)
print("Transcription result:", text)
