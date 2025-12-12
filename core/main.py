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
from core.intent_router import IntentRouter

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

    # Shared EventBus
    bus = EventBus()

    # Core engine
    engine = build_engine(event_bus=bus)

    # Intent router (Think-Before-Speak gate)
    intent_router = IntentRouter()
    
    # --- Stream/UI permission events (hotkeys publish these now; UI will later too) ---
    def handle_auto_reply_set(data):
        payload = data or {}
        enabled = bool(payload.get("enabled", False))
        intent_router.set_auto_reply(enabled)
        log.info(f"Auto-reply set -> {enabled}")

    def handle_respond_now(_data):
        intent_router.trigger_respond_now()
        log.info("Respond-now requested")

    def handle_respond_suggestion(_data):
        intent_router.trigger_respond_to_suggestion()
        log.info("Respond-to-suggestion requested")

    bus.subscribe("ui.auto_reply.set", handle_auto_reply_set)
    bus.subscribe("ui.respond_now", handle_respond_now)
    bus.subscribe("ui.respond_suggestion", handle_respond_suggestion)


    # Local TTS
    tts = LocalTTS()

    # Hotkeys
    start_hotkeys(event_bus=bus)

    # Voice listener (STT)
    start_voice_listener(bus)

    # Handle transcribed voice input
    def handle_voice_transcribed(data):
        payload = data or {}
        text = payload.get("text", "")

        if not isinstance(text, str):
            log.warning(f"voice.transcribed received non-string text: {type(text)}")
            return

        text = text.strip()

        if not text:
            log.info("voice.transcribed event received with empty text.")
            fallback = (
                "I heard something, but I could not understand the words. "
                "Please say it again."
            )
            try:
                print(f"\nAI (voice): {fallback}\n")
                tts.speak(fallback)
            except Exception as exc:
                log.exception(f"Error speaking fallback for empty STT text: {exc}")
            return

        log.info(f"Voice input text: {text!r}")

        # Register voice input as a chat-style message
        intent_router.register_chat_message({
            "user": "voice",
            "text": text,
            "source": "voice_input",
        })

        try:
            # Let the intent router decide if speech is allowed
            final_reply = intent_router.route_intent(
                ai_engine=engine,
                vision_description=None,  # vision plugs in later
            )
        except Exception as exc:
            log.exception(f"Error routing voice intent: {exc}")
            return

        # Speak only if router approved a response
        if final_reply:
            try:
                print(f"\nAI (voice): {final_reply}\n")
                tts.speak(final_reply)
            except Exception as exc:
                log.exception(f"Error printing or speaking AI voice reply: {exc}")
        else:
            log.info("IntentRouter suppressed speech output.")

    # Subscribe to voice events
    bus.subscribe("voice.transcribed", handle_voice_transcribed)

    print_startup_banner(engine)
    interactive_loop(engine)

    log.info("Shutting down Master AI Co-Partner core.main")


if __name__ == "__main__":
    main()
