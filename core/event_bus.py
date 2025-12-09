"""
event_bus.py
Centralized event routing system for AI Co-Partner.
Allows different modules to subscribe and publish events without hard dependencies.
"""

from typing import Callable, Dict, List, Any
from core.logger import get_logger

log = get_logger("event_bus")


class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        log.info("EventBus initialized.")

    def subscribe(self, event_name: str, callback: Callable):
        """Register a callback to be called when an event fires."""
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        self._subscribers[event_name].append(callback)
        log.info(f"Subscribed to event '{event_name}' with callback {callback.__name__}")

    def publish(self, event_name: str, data: Any = None):
        """Trigger an event and call all subscribers."""
        if event_name not in self._subscribers:
            log.warning(f"No subscribers for event '{event_name}'")
            return

        log.info(f"Publishing event '{event_name}' with data: {data}")

        for callback in self._subscribers[event_name]:
            try:
                callback(data)
            except Exception as e:
                log.error(f"Error in callback '{callback.__name__}': {e}")
