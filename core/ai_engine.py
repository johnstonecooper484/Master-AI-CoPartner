"""
ai_engine.py
Core reasoning engine for the AI Co-Partner.
Handles message processing, personality injection, and memory integration.
"""

from typing import Optional, Dict, Any
import os

from openai import OpenAI
from dotenv import load_dotenv

from core.logger.logger import get_logger
from core.event_bus import EventBus
from core.memory.memory_manager import MemoryManager


log = get_logger("ai_engine")

load_dotenv()
client = OpenAI()


class AIEngine:
    def __init__(self, event_bus: EventBus, memory: Optional[MemoryManager] = None):
        self.bus = event_bus
        self.memory = memory
        log.info(f"AIEngine initialized (memory_attached={bool(memory)})")

    def _infer_priority(self, message: str) -> str:
        """
        Very simple 'human-ish' rule system to decide if something
        should be treated as important.
        """
        text = message.lower()

        trigger_words = [
            "remember this",
            "don't forget",
            "dont forget",
            "save this",
            "i'll need this",
            "i will need this",
            "this is important",
        ]

        for t in trigger_words:
            if t in text:
                return "high"

        return "normal"

    def process(
        self,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Main processing pipeline.

        Right now:
        - logs the message
        - optionally stores it in memory
        - fires events on the event bus
        - calls OpenAI for a real response
        """
        if metadata is None:
            metadata = {}

        log.info(f"Processing message: {message!r}")

        # Decide memory priority
        priority = self._infer_priority(message)
        metadata.setdefault("source", "ai_engine")
        metadata.setdefault("priority", priority)

        # Store in memory if available
        if self.memory is not None:
            try:
                self.memory.add_memory(message, metadata)
                log.info(f"Stored message in memory with priority={priority}")
            except Exception as e:
                log.error(f"Failed to store memory: {e}")

        # Publish events so other systems can react
        self.bus.publish("ai_input", {"text": message, "metadata": metadata})

        # Use OpenAI to generate a real response
        try:
            model_name = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are the user's local AI Co-Partner assistant running on their machine. "
                            "Be clear, practical, concise, and supportive. The user may have ADHD and "
                            "memory issues, so keep explanations short and step-by-step when needed."
                        ),
                    },
                    {
                        "role": "user",
                        "content": message,
                    },
                ],
            )
            response = completion.choices[0].message.content
        except Exception as e:
            log.error(f"OpenAI chat completion failed: {e}")
            response = "I ran into a problem talking to my AI model. Check your API key, internet connection, and logs."

        self.bus.publish("ai_response", {"text": response, "metadata": metadata})
        log.info(f"Generated response: {response!r}")

        return response


if __name__ == "__main__":
    # Simple standalone self-test
    from core.event_bus import EventBus
    from core.memory.memory_manager import MemoryManager

    bus = EventBus()
    mem = MemoryManager()
    engine = AIEngine(bus, mem)

    test_text = "Remember this, I will need this later."
    reply = engine.process(test_text, {"source": "ai_engine_self_test"})
    print("Self-test reply:", reply)
    print("AIEngine self-test complete.")
