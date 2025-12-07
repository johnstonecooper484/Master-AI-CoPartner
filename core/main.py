"""
main.py
Entry point for the AI Co-Partner system.
For now this just wires up logging + the event bus and runs a simple test.
"""

from config import settings
from core.event_bus import EventBus
from core.logger.logger import get_logger
from core.command_handler import CommandHandler

log = get_logger("core_main")


def on_test_event(data):
    """Simple example event handler."""
    log.info(f"Received test event with data: {data}")


def main():
    print("[System] AI Co-Partner starting up...")
    log.info("=== AI Co-Partner starting up ===")

    # Create the central event bus
    bus = EventBus()

    # Initialize command handler
    cmd = CommandHandler()
    log.info(f"CommandHandler ready: {cmd}")

    # Subscribe a test handler
    bus.subscribe("test_event", on_test_event)

    # Fire a test event so we can see logs working
    bus.publish("test_event", {"msg": "Hello from main loop"})

    # Test the command handler
    result = cmd.handle_command("ping")
    log.info(f"Command test result: {result}")
    print(f"[Command] Test result: {result}")

    log.info(f"Debug mode: {settings.DEBUG}")
    log.info("=== AI Co-Partner initial main() finished ===")
    print("[System] AI Co-Partner main() finished.")


if __name__ == "__main__":
    main()
