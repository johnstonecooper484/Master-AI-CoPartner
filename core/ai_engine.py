"""ai_engine.py - AI core engine for Master AI Co-Partner."""

from __future__ import annotations

from typing import Optional, Dict, Any
import os
from pathlib import Path

import requests

from config import settings
from core.logger import get_logger
from core.event_bus import EventBus
from core.memory.memory_manager import MemoryManager

log = get_logger("ai_engine")


def _load_project_env() -> None:
    """
    Ensure the .env in the project root is loaded.

    This ignores any random .env files in subfolders and always targets:
    <project_root>/.env
    """
    try:
        from dotenv import load_dotenv

        project_root = Path(__file__).resolve().parents[1]  # .../Master-AI-CoPartner/
        env_path = project_root / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=False)
            log.info("Loaded .env from %s", env_path)
        else:
            log.warning(".env not found at %s", env_path)
    except Exception as e:
        log.error("Failed to load project .env: %s", e)


class AIEngine:
    def __init__(
        self,
        event_bus: EventBus,
        memory: Optional[MemoryManager] = None,
        offline_only: Optional[bool] = None,
    ) -> None:
        self.bus = event_bus
        self.memory = memory
        self.offline_only = (
            settings.OFFLINE_ONLY if offline_only is None else offline_only
        )

        log.info(
            "AIEngine initialized (memory_attached=%s, offline_only=%s)",
            bool(memory),
            self.offline_only,
        )

    # ---------------------------------------------------------
    # Priority / memory handling
    # ---------------------------------------------------------

    def _infer_priority(self, message: str, metadata: Dict[str, Any]) -> str:
        text = message.lower()

        high_markers = [
            "remember this",
            "don't forget",
            "important",
            "my schedule",
            "medical",
            "emergency",
            "password",
            "login",
        ]
        todo_markers = [
            "remind me",
            "i need to",
            "i have to",
            "i must",
            "todo",
            "task",
        ]

        if any(m in text for m in high_markers) or any(
            m in text for m in todo_markers
        ):
            return "high"

        if len(text) < 10:
            return "low"

        return "normal"

    # ---------------------------------------------------------
    # Main entry
    # ---------------------------------------------------------

    def process(self, message: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        if metadata is None:
            metadata = {}

        source = metadata.get("source", "unknown")
        log.info("AIEngine.process called from source=%r", source)

        priority = self._infer_priority(message, metadata)
        log.info("Inferred memory priority=%r", priority)

        # Store to memory
        if self.memory:
            try:
                self.memory.store_message(
                    message=message,
                    metadata=metadata,
                    priority=priority,
                )
                log.info("Stored message in memory with priority=%s", priority)
            except Exception as e:
                log.exception("Failed to store message in memory: %s", e)

        # Publish "received" event
        try:
            self.bus.publish(
                "ai.message_received",
                {
                    "message": message,
                    "metadata": metadata,
                    "priority": priority,
                },
            )
        except Exception as e:
            log.exception("Failed to publish message_received event: %s", e)

        # Decide offline vs online
        online_enabled = getattr(settings, "ONLINE_FEATURES_ENABLED", False)
        if self.offline_only or not online_enabled:
            log.info("Using OFFLINE response path.")
            reply = self._call_offline(message, metadata)
        else:
            try:
                reply = self._call_online(message, metadata)
            except Exception as e:
                log.exception(
                    "Online call failed; falling back to offline. Error: %s", e
                )
                reply = self._call_offline(message, metadata)

        # Publish "replied" event
        try:
            self.bus.publish(
                "ai.message_replied",
                {
                    "message": message,
                    "reply": reply,
                    "metadata": metadata,
                    "priority": priority,
                },
            )
        except Exception as e:
            log.exception("Failed to publish message_replied event: %s", e)

        return reply

    # ---------------------------------------------------------
    # OFFLINE / LOCAL LLM PATH
    # ---------------------------------------------------------

    def _call_offline(self, message: str, metadata: Dict[str, Any]) -> str:
        """Offline mode with optional local model support (LM Studio)."""

        # Make sure env is loaded from project root
        _load_project_env()

        local_endpoint = os.getenv("LOCAL_LLM_ENDPOINT")
        local_model_id = os.getenv("LOCAL_LLM_MODEL_ID", "google_gemma-3-4b-it")

        # DEBUG: see what env vars we actually have at runtime
        log.info("DEBUG LOCAL_LLM_ENDPOINT = %r", local_endpoint)
        log.info("DEBUG LOCAL_LLM_MODEL_ID = %r", local_model_id)

        if local_endpoint:
            log.info("Attempting LOCAL LLM endpoint: %s", local_endpoint)

            try:
                payload = {
                    "model": local_model_id,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are John's local AI Co-Partner running on his PC. "
                                "Be concise, practical, and supportive. He has dyslexia "
                                "and memory issues, so keep answers clear and step-by-step."
                            ),
                        },
                        {"role": "user", "content": message},
                    ],
                }

                response = requests.post(local_endpoint, json=payload, timeout=30)

                if response.ok:
                    data = response.json()
                    choices = data.get("choices") or []
                    if choices:
                        msg = choices[0].get("message", {}) or {}
                        text = msg.get("content") or choices[0].get("text")
                        if text:
                            log.info("Local LLM responded successfully.")
                            return text.strip()
                    log.warning(
                        "Local LLM returned no usable text; falling back to stub."
                    )
                else:
                    log.warning(
                        "Local LLM HTTP error %s: %s",
                        response.status_code,
                        response.text[:200],
                    )
            except Exception as e:
                log.error("Local LLM call failed: %s", e)

        # Stub fallback if no endpoint or failure
        log.info("Using OFFLINE stub response path.")
        trimmed = message.strip()

        if not trimmed:
            return "I'm in offline mode, and you did not give me much to work with."

        return (
            "Offline brain v0 here. I do not have a full local model yet, but I heard you say:\n"
            f"→ {trimmed}\n\n"
            "When you give me a real local model endpoint, I'll start thinking much deeper."
        )

    # ---------------------------------------------------------
    # ONLINE / OPENAI PATH
    # ---------------------------------------------------------

    def _call_online(self, message: str, metadata: Dict[str, Any]) -> str:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            log.warning("OPENAI_API_KEY not set; falling back to offline stub.")
            return self._call_offline(message, metadata)

        log.info("Calling OpenAI online API path.")
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            # These should come from config.settings
            model_name = getattr(settings, "OPENAI_MODEL_NAME", "gpt-4o-mini")
            url = getattr(
                settings,
                "OPENAI_CHAT_COMPLETIONS_URL",
                "https://api.openai.com/v1/chat/completions",
            )

            payload = {
                "model": model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are an AI Co-Partner helping John with coding, "
                            "projects, and daily life. Be practical, step-by-step, "
                            "and supportive."
                        ),
                    },
                    {"role": "user", "content": message},
                ],
            }

            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if not response.ok:
                log.warning(
                    "OpenAI HTTP error %s: %s",
                    response.status_code,
                    response.text[:200],
                )
                return self._call_offline(message, metadata)

            data = response.json()
            choices = data.get("choices") or []
            if not choices:
                log.warning("OpenAI returned no choices; falling back to offline.")
                return self._call_offline(message, metadata)

            msg = choices[0].get("message", {}) or {}
            text = msg.get("content") or choices[0].get("text")

            if not text:
                log.warning("OpenAI choice has no text; falling back to offline.")
                return self._call_offline(message, metadata)

            return text.strip()

        except Exception as e:
            log.exception("OpenAI call failed; falling back to offline: %s", e)
            return self._call_offline(message, metadata)


if __name__ == "__main__":
    # Simple standalone test
    bus = EventBus()
    memory = MemoryManager()
    engine = AIEngine(bus, memory, offline_only=True)

    print("=== AIEngine interactive test ===")
    print("Type something and press Enter. Type 'quit' to exit.")

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
