from __future__ import annotations

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=False)

"""main.py

Top-level entrypoint for the Master AI Co-Partner.
"""

from typing import Optional

from core.io.speech.tts_local import LocalTTS
from config import settings
from core.logger import get_logger
from core.event_bus import EventBus
from core.memory.memory_manager import MemoryManager
from core.ai_engine import AIEngine
from core.hotkeys import start_hotkeys
from core.io.speech.listener import start_voice_listener

log = get_logger("core_main")


def build_engine(
    offline_only: Optional[bool] = None,
    event_bus: Optional[EventBus] = None,
) -> AIEngine:
    """Factory to build the AIEngine with standard wiring."""
    bus = event_bus or EventBus()
    memory = MemoryManager()
    engine = AIEngine(event_bus=bus, memory=memory, offline_only=offline_only)
    return engine


def print_startup_banner(engine: AIEngine) -> None:
    mode = "OFFLINE" if engine.offline_only else "ONLINE-capable"
    print("=== Master AI Co-Partner ===")
    print(f"Active mode: {settings.ACTIVE_MODE}")
    print(f"Mode: {mode}")
    print("Type something and press Enter. Type 'quit' to exit.\n")


def interactive_loop(engine: AIEngine) -> None:
    """Very simple text-based UI."""
    while True:
        try:
            text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[Exiting Co-Partner main loop]")
            break

        if not text:
            continue
        if text.lower() in {"quit", "exit"}:
            print("[Goodbye from Co-Partner]")
            break

        reply = engine.process(text, {"source": "core_main_cli"})
        print("AI:", reply)
        print()


def main() -> None:
    """Main entrypoint used by `python -m core.main`."""
    log.info("Starting Master AI Co-Partner core.main")

    # Create a shared EventBus so engine, hotkeys, and voice listener see the same events
    bus = EventBus()

    # Build the engine using that shared bus
    engine = build_engine(event_bus=bus)

    # Add local TTS for voice replies
    tts = LocalTTS()

    # Start global hotkeys (F12 toggle) using the same bus
    start_hotkeys(event_bus=bus)

    # Start the voice listener that reacts to F12 listen_toggle events
    start_voice_listener(bus)

    # Route transcribed voice text into the AI engine
    def handle_voice_transcribed(data):
        # data is expected to be a dict like {"text": "..."}
        payload = data or {}
        text = payload.get("text", "")

        if not isinstance(text, str):
            log.warning(f"voice.transcribed received non-string text: {type(text)}")
            return

        text = text.strip()

        # NEW: if empty text, still give spoken feedback
        if not text:
            log.info("voice.transcribed event received with empty text.")
            fallback = "I heard something, but I could not understand the words. Please say it again."
            try:
                print(f"\nAI (voice): {fallback}\n")
                tts.speak(fallback)
            except Exception as exc:
                log.exception(f"Error speaking fallback for empty STT text: {exc}")
            return

        log.info(f"Voice input text: {text!r}")

        try:
            # Process this like a normal user message, but mark it as voice input
            reply = engine.process(text, {"source": "voice_input"})
        except Exception as exc:
            log.exception(f"Error processing voice input: {exc}")
            return

        # Console echo + spoken reply
        try:
            print(f"\nAI (voice): {reply}\n")
            tts.speak(reply)
        except Exception as exc:
            log.exception(f"Error printing or speaking AI voice reply: {exc}")

    # Subscribe the handler to the EventBus
    bus.subscribe("voice.transcribed", handle_voice_transcribed)

    print_startup_banner(engine)
    interactive_loop(engine)

    log.info("Shutting down Master AI Co-Partner core.main")


if __name__ == "__main__":
    main()
