"""
core_manager.py
Central orchestrator for the AI Co-Partner system.
Initializes all core modules and connects them to the event bus.
"""

from core.logger.logger import get_logger
from core.event_bus import EventBus
from core.ai_engine import AIEngine

log = get_logger("core_manager")


class CoreManager:
    def __init__(self):
        log.info("CoreManager initializing...")
        self.event_bus = EventBus()
        self.ai = AIEngine(self.event_bus)
        log.info("CoreManager initialized successfully.")

    def handle_input(self, text: str):
        """Send text to the AI engine for processing."""
        log.info(f"CoreManager received input: {text}")
        return self.ai.process(text)
