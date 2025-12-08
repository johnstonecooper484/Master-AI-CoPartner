"""main.py

Top-level entrypoint for the Master AI Co-Partner.

Right now this:
- Sets up EventBus, MemoryManager, and AIEngine
- Prints current mode (offline / online)
- Starts a simple CLI loop so John can talk to the system

Later this will be replaced / extended with:
- Hotkey handler
- Voice I/O
- Multi-machine coordination
"""

from __future__ import annotations

from typing import Optional

from config import settings
from core.logger import get_logger
from core.event_bus import EventBus
from core.memory.memory_manager import MemoryManager
from core.ai_engine import AIEngine

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
    print(f"Active mode: {mode}")
    print(f"Settings ACTIVE_MODE: {settings.ACTIVE_MODE}")
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

    # For now, we trust settings / engine defaults to decide offline vs online.
    engine = build_engine()

    print_startup_banner(engine)
    interactive_loop(engine)

    log.info("Shutting down Master AI Co-Partner core.main")


if __name__ == "__main__":
    main()
