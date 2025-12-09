from __future__ import annotations

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=False)

"""main.py

Top-level entrypoint for the Master AI Co-Partner.
"""

from typing import Optional

from config import settings
from core.logger import get_logger
from core.event_bus import EventBus
from core.memory.memory_manager import MemoryManager
from core.ai_engine import AIEngine
from core.hotkeys import start_hotkeys  # 🔹 add this line

log = get_logger("core_main")


def build_engine(offline_only: Optional[bool] = None) -> AIEngine:
    """Factory to build the AIEngine with standard wiring."""
    bus = EventBus()
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

    # Build the engine (includes EventBus + MemoryManager wiring internally)
    engine = build_engine()

    # Start global hotkeys (F12 toggle) in the background
    # Right now this just logs ON/OFF and is ready to be wired into voice later.
    start_hotkeys()

    print_startup_banner(engine)
    interactive_loop(engine)

    log.info("Shutting down Master AI Co-Partner core.main")



if __name__ == "__main__":
    main()
