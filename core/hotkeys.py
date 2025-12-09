# core/hotkeys.py
from __future__ import annotations

from typing import Optional, Callable
import threading

import keyboard  # Requires: pip install keyboard

from core.logger import get_logger
from core.event_bus import EventBus

log = get_logger("hotkeys")


class HotkeyListener:
    """
    Listens for global hotkeys (currently F12) and triggers actions.

    - F12 toggles a "listening" state (True/False)
    - Optionally publishes an event on the EventBus:
        event_name: "voice.listen_toggle"
        data: {"listening": bool}
    - Optionally calls a custom callback: on_toggle(is_listening: bool)
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        on_toggle: Optional[Callable[[bool], None]] = None,
    ) -> None:
        self._event_bus = event_bus
        self._on_toggle = on_toggle
        self._listening: bool = False
        self._thread: Optional[threading.Thread] = None

    @property
    def listening(self) -> bool:
        """Current listening state (True = listening, False = idle)."""
        return self._listening

    def start(self) -> None:
        """
        Start the hotkey listener in a background thread.
        Safe to call once; extra calls will be ignored with a warning.
        """
        if self._thread and self._thread.is_alive():
            log.warning("HotkeyListener.start() called but listener is already running.")
            return

        self._thread = threading.Thread(
            target=self._run,
            name="HotkeyListenerThread",
            daemon=True,
        )
        self._thread.start()
        log.info("HotkeyListener thread started (F12 toggle).")

    def _run(self) -> None:
        """
        Internal loop that registers the F12 hotkey
        and then waits forever for keyboard events.
        """
        log.info("Registering F12 hotkey for listen toggle.")
        keyboard.add_hotkey("f12", self._handle_f12)

        # Block this background thread forever, until process exits.
        # Keyboard hooks still work even though this is in a daemon thread.
        try:
            keyboard.wait()  # Wait for any key event, effectively "run forever"
        except Exception as exc:
            log.exception(f"Keyboard wait loop crashed: {exc}")

        log.info("HotkeyListener thread exiting (keyboard.wait() returned).")

    def _handle_f12(self) -> None:
        """
        Handler called whenever F12 is pressed.
        Toggles internal listening state and notifies listeners.
        """
        try:
            self._listening = not self._listening
            state_label = "ON" if self._listening else "OFF"

            log.info(f"F12 pressed: toggling listening state to {state_label}")

            # Publish event to the event bus, if provided
            if self._event_bus is not None:
                try:
                    self._event_bus.publish(
                        "voice.listen_toggle",
                        {"listening": self._listening},
                    )
                except Exception as exc:
                    log.exception(f"Error publishing voice.listen_toggle: {exc}")

            # Call optional callback, if provided
            if self._on_toggle is not None:
                try:
                    self._on_toggle(self._listening)
                except Exception as exc:
                    log.exception(f"Error in on_toggle callback: {exc}")

        except Exception as exc:
            log.exception(f"Unexpected error handling F12 hotkey: {exc}")


def start_hotkeys(
    event_bus: Optional[EventBus] = None,
    on_toggle: Optional[Callable[[bool], None]] = None,
) -> HotkeyListener:
    """
    Convenience helper:

    - Creates a HotkeyListener
    - Starts it in the background
    - Returns the instance (so other code can inspect .listening)

    This is what other parts of the system will call.
    """
    listener = HotkeyListener(event_bus=event_bus, on_toggle=on_toggle)
    listener.start()
    return listener


if __name__ == "__main__":
    """
    Standalone test mode:
    Run:  python -m core.hotkeys

    Then press F12 and watch your logs / console for:
        "F12 pressed: toggling listening state to ON/OFF"
    Ctrl+C to stop.
    """
    import time

    log.info("Starting standalone hotkey test. Press F12 to toggle. Ctrl+C to exit.")
    listener = start_hotkeys(event_bus=None, on_toggle=None)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Standalone hotkey test stopped by user.")
