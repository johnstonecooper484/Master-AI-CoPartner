"""ai_engine.py

Core reasoning engine for the AI Co-Partner.

- Handles message processing
- Applies simple priority rules for memory
- Publishes events
- Chooses OFFLINE vs ONLINE generation based on config/settings
"""

from __future__ import annotations

from typing import Optional, Dict, Any
import os

from dotenv import load_dotenv
from openai import OpenAI

from config import settings
from core.logger import get_logger
from core.event_bus import EventBus
from core.memory.memory_manager import MemoryManager

log = get_logger("ai_engine")

load_dotenv()
client = OpenAI()


class AIEngine:
    """Main brain wrapper for the Co-Partner."""

    def __init__(
        self,
        event_bus: EventBus,
        memory: Optional[MemoryManager] = None,
        offline_only: Optional[bool] = None,
    ):
        self.bus = event_bus
        self.memory = memory
        # If not explicitly overridden, follow global settings
        self.offline_only = (
            settings.OFFLINE_ONLY if offline_only is None else offline_only
        )

        log.info(
            "AIEngine initialized "
            f"(memory_attached={bool(memory)}, offline_only={self.offline_only})"
        )

    # ------------------------------------------------------------------
    # Priority tagging for memory
    # ------------------------------------------------------------------
    def _infer_priority(self, message: str) -> str:
        """Very simple rule to decide if something is 'important'."""
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

    # ------------------------------------------------------------------
    # Offline vs online routing
    # ------------------------------------------------------------------
    def _call_offline(self, message: str, metadata: Dict[str, Any]) -> str:
        """Offline stub response (v0).

        This keeps the system usable with no internet or API key.
        Later, this will call a real local LLM.
        """
        log.info("Using OFFLINE response path.")
        # Super simple behaviour for now:
        # - acknowledge offline mode
        # - lightly echo what was said
        # - keep it short and practical
        trimmed = message.strip()
        if not trimmed:
            return "I'm in offline mode and you didn't say much. Try again with a bit more detail."

        return (
            "Offline brain v0 here. I don't have a full local model yet, but I heard you say:\n"
            f"→ {trimmed}\n\n"
            "For now I can help you organize tasks, next steps, and simple logic. "
            "When we wire in the real local model, I'll get a lot smarter."
        )

    def _call_online(self, message: str, metadata: Dict[str, Any]) -> str:
        """Online response via OpenAI, with safe fallback to offline stub."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            log.warning("OPENAI_API_KEY not set; falling back to offline path.")
            return self._call_offline(message, metadata)

        try:
            model_name = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are John's local AI Co-Partner assistant running on his machine. "
                            "Be clear, practical, concise, and supportive. John has ADHD, dyslexia, "
                            "and memory issues, so keep explanations short and step-by-step when needed. "
                            "Follow the Master Control and Blueprint rules baked into this system."
                        ),
                    },
                    {
                        "role": "user",
                        "content": message,
                    },
                ],
            )
            response = completion.choices[0].message.content
            log.info("Received response from OpenAI backend.")
            return response

        except Exception as e:
            log.error(f"OpenAI chat completion failed: {e}")
            return self._call_offline(message, metadata)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def process(
        self,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Main processing pipeline.

        - logs the message
        - optionally stores it in memory
        - fires events on the event bus
        - chooses OFFLINE or ONLINE response path
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

        # Decide which brain to use
        if self.offline_only or settings.ACTIVE_MODE == settings.MODE_OFFLINE_ONLY:
            response = self._call_offline(message, metadata)
        else:
            response = self._call_online(message, metadata)

        # Publish response for other modules
        self.bus.publish("ai_response", {"text": response, "metadata": metadata})
        log.info(f"Generated response: {response!r}")

        return response


# ----------------------------------------------------------------------
# Simple standalone interactive test
# ----------------------------------------------------------------------
if __name__ == "__main__":
    from core.event_bus import EventBus
    from core.memory.memory_manager import MemoryManager

    bus = EventBus()
    mem = MemoryManager()
    engine = AIEngine(bus, mem)

    print("=== AIEngine interactive test ===")
    print("Type something and press Enter. Type 'quit' to exit.\n")

    while True:
        try:
            text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[Exiting AIEngine interactive test]")
            break

        if not text:
            continue
        if text.lower() in {"quit", "exit"}:
            print("[Goodbye from AIEngine test]")
            break

        reply = engine.process(text, {"source": "ai_engine_cli"})
        print("AI:", reply)
        print()
