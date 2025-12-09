"""
core.io.speech.tts_local
Local offline Text-To-Speech for AI Co-Partner.
"""

import pyttsx3
from core.logger import get_logger

log = get_logger("tts_local")


class LocalTTS:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 185)
        self.engine.setProperty("volume", 1.0)
        log.info("Local TTS engine initialized.")

    def speak(self, text: str):
        if not text:
            return

        log.info(f"TTS speaking: {text}")
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            log.error(f"TTS speak error: {e}")


# ✅ Standalone test
if __name__ == "__main__":
    tts = LocalTTS()
    tts.speak("Voice system online. Hello John.")
