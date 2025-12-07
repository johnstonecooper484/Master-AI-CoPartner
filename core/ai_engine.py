"""
ai_engine.py
Core reasoning engine for the AI Co-Partner.
Handles message processing, personality injection, and future LLM integration.
"""

from core.logger.logger import get_logger
from core.event_bus import EventBus

log = get_logger("ai_engine")


class AIEngine:
    def __init__(self, event_bus: EventBus):
        self.bus = event_bus
        log.info("AIEngine initialized.")

    def process(self, message: str) -> str:
        """
        Placeholder for the main reasoning pipeline.
        Later this will call the LLM, apply personality modules, memory, etc.
        """
        log.info(f"Processing message: {message}")

        # Temporary demo response
        response = f"AIEngine heard: {message}"

        # Notify system that a response was generated
        self.bus.publish("ai_response", response)

        return response
