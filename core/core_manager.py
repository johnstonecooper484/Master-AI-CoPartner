"""
core_manager.py
Central orchestrator for the AI Co-Partner system.
Initializes all core modules and connects them to the event bus.
"""

from core.logger.logger import get_logger
from core.event_bus import EventBus
from core.ai_engine import AIEngine
from core.memory.memory_manager import MemoryManager

log = get_logger("core_manager")


class CoreManager:
    def __init__(self):
        log.info("CoreManager initializing...")

        # core systems
        self.event_bus = EventBus()
        self.memory = MemoryManager()
        self.ai = AIEngine(self.event_bus, self.memory)

        log.info("CoreManager initialized successfully.")

    def handle_input(self, text: str):
        """Send text to the AI engine for processing."""
        log.info(f"CoreManager received input: {text}")
        return self.ai.process(text, {"source": "core_manager"})


if __name__ == "__main__":
    cm = CoreManager()

    # send a test line that should be treated as important
    test_line = "Hey, remember this config, I will need this later."
    reply = cm.handle_input(test_line)
    print("CoreManager test reply:", reply)
    print("CoreManager self-test complete.")
