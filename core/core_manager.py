"""
core_manager.py
Central orchestrator for the AI Co-Partner system.
Initializes all core modules and connects them to the event bus.
"""

from core.logger import get_logger
from core.event_bus import EventBus
from core.ai_engine import AIEngine
from core.memory.memory_manager import MemoryManager
from core.command_handler import CommandHandler

log = get_logger("core_manager")


class CoreManager:
    def __init__(self):
        log.info("CoreManager initializing...")

        # core systems
        self.event_bus = EventBus()
        self.memory = MemoryManager()
        self.ai = AIEngine(self.event_bus, self.memory)
        self.command_handler = CommandHandler()

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
        """Simple console loop: commands with /, chat goes to AI."""
        log.info("CoreManager text loop starting.")
        print("AI Co-Partner online. Type your message, or /quit to exit.")
        print("Use /ping or /help for basic commands (with or without /).")

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
                log.info("Exit command received, stopping loop.")
                break

            # If it starts with /, treat as a command
            if user_input.startswith("/"):
                cmd_text = user_input.lstrip("/")
                result = self.command_handler.handle_command(
                    cmd_text,
                    source="cli",
                    session_id=None,
                )
                print(f"[Command] {result['status']}: {result['message']}")
                continue

            # Otherwise pass it to the AI engine
            reply = self.handle_input(user_input)
            print(f"AI: {reply}")

        log.info("CoreManager text loop ended.")


if __name__ == "__main__":
    cm = CoreManager()
    cm.run_text_loop()
