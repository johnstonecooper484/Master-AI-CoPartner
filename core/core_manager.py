"""
core_manager.py
Central orchestrator for the AI Co-Partner system.
Now includes live voice output via LocalTTS.
"""

from core.logger import get_logger
from core.event_bus import EventBus
from core.ai_engine import AIEngine
from core.memory.memory_manager import MemoryManager
from core.command_handler import CommandHandler
from core.io.speech.tts_local import LocalTTS  # ✅ VOICE

log = get_logger("core_manager")


class CoreManager:
    def __init__(self):
        log.info("CoreManager initializing...")

        # core systems
        self.event_bus = EventBus()
        self.memory = MemoryManager()
        self.ai = AIEngine(self.event_bus, self.memory)
        self.command_handler = CommandHandler()
        self.tts = LocalTTS()  # ✅ activate voice engine

        # subscribe to AI events for logging
        self.event_bus.subscribe("ai.message_received", self._on_ai_message_received)
        self.event_bus.subscribe("ai.message_replied", self._on_ai_message_replied)

        log.info("CoreManager initialized successfully.")

    def handle_input(self, text: str):
        """Send text to the AI engine for processing."""
        log.info(f"CoreManager received input: {text}")
        return self.ai.process(text, {"source": "core_manager"})

    def _on_ai_message_received(self, data):
        log.info(f"[EVENT] AI received message: {data}")

    def _on_ai_message_replied(self, data):
        log.info(f"[EVENT] AI replied with: {data}")

    def run_text_loop(self) -> None:
        """Console loop: commands + AI + LIVE VOICE."""
        log.info("CoreManager text loop starting.")
        print("AI Co-Partner online. Type your message, or /quit to exit.")

        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n[CoreManager] Shutting down from keyboard/EOF.")
                log.info("CoreManager loop interrupted, shutting down.")
                break

            if not user_input:
                continue

            lowered = user_input.lower()
            if lowered in ("/quit", "/exit", "/q"):
                print("AI: Goodbye for now.")
                self.tts.speak("Goodbye for now.")
                log.info("Exit command received, stopping loop.")
                break

            # Commands
            if user_input.startswith("/"):
                cmd_text = user_input.lstrip("/")
                result = self.command_handler.handle_command(
                    cmd_text,
                    source="cli",
                    session_id=None,
                )
                print(f"[Command] {result['status']}: {result['message']}")
                self.tts.speak(result["message"])
                continue

            # Normal AI chat
            reply = self.handle_input(user_input)
            print(f"AI: {reply}")

            # ✅ SPEAKS THE REAL AI RESPONSE
            self.tts.speak(reply)

        log.info("CoreManager text loop ended.")


if __name__ == "__main__":
    cm = CoreManager()
    cm.run_text_loop()
