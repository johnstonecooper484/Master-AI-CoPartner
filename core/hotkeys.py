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
    Listens for global hotkeys and triggers actions.

    Existing:
    - F12 toggles a "listening" state (True/False)
      Publishes: "voice.listen_toggle" with {"listening": bool}

    Added (stream permission gates; UI will mirror these later):
    - Ctrl+Shift+F10 toggles auto-reply master switch
      Publishes: "ui.auto_reply.set" with {"enabled": bool}

    - Ctrl+Shift+F11 triggers "respond now" (one-shot)
      Publishes: "ui.respond_now"

    - Ctrl+Shift+F12 triggers "respond to suggestion" (one-shot)
      Publishes: "ui.respond_suggestion"
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        on_toggle: Optional[Callable[[bool], None]] = None,
    ) -> None:
        self._event_bus = event_bus
        self._on_toggle = on_toggle

        self._listening: bool = False
        self._auto_reply_enabled: bool = False

        self._thread: Optional[threading.Thread] = None

    @property
    def listening(self) -> bool:
        return self._listening

    @property
    def auto_reply_enabled(self) -> bool:
        return self._auto_reply_enabled

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            log.warning("HotkeyListener.start() called but listener is already running.")
            return

        self._thread = threading.Thread(
            target=self._run,
            name="HotkeyListenerThread",
            daemon=True,
        )
        self._thread.start()
        log.info("HotkeyListener thread started (F12 + Ctrl+Shift+F10/F11/F12).")

    def _run(self) -> None:
        log.info("Registering hotkeys.")

        # Keep your existing F12 behavior
        keyboard.add_hotkey("f12", self._handle_f12)

        # Stream permission gates (chosen to avoid typing into terminal / F9 issues)
        keyboard.add_hotkey("ctrl+shift+f10", self._handle_toggle_auto_reply)
        keyboard.add_hotkey("ctrl+shift+f11", self._handle_respond_now)
        keyboard.add_hotkey("ctrl+shift+f12", self._handle_respond_suggestion)

        try:
            keyboard.wait()
        except Exception as exc:
            log.exception(f"Keyboard wait loop crashed: {exc}")

        log.info("HotkeyListener thread exiting (keyboard.wait() returned).")

    def _publish(self, event_name: str, data: Optional[dict] = None) -> None:
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(event_name, data or {})
        except Exception as exc:
            log.exception(f"Error publishing {event_name}: {exc}")

    def _handle_f12(self) -> None:
        try:
            self._listening = not self._listening
            state_label = "ON" if self._listening else "OFF"
            log.info(f"F12 pressed: toggling listening state to {state_label}")

            self._publish("voice.listen_toggle", {"listening": self._listening})

            if self._on_toggle is not None:
                try:
                    self._on_toggle(self._listening)
                except Exception as exc:
                    log.exception(f"Error in on_toggle callback: {exc}")

        except Exception as exc:
            log.exception(f"Unexpected error handling F12 hotkey: {exc}")

    def _handle_toggle_auto_reply(self) -> None:
        try:
            self._auto_reply_enabled = not self._auto_reply_enabled
            state_label = "ON" if self._auto_reply_enabled else "OFF"
            log.info(f"Ctrl+Shift+F10 pressed: toggling AUTO-REPLY to {state_label}")

            self._publish("ui.auto_reply.set", {"enabled": self._auto_reply_enabled})
        except Exception as exc:
            log.exception(f"Unexpected error handling auto-reply toggle: {exc}")

    def _handle_respond_now(self) -> None:
        try:
            log.info("Ctrl+Shift+F11 pressed: RESPOND NOW")
            self._publish("ui.respond_now", {})
        except Exception as exc:
            log.exception(f"Unexpected error handling respond-now: {exc}")

    def _handle_respond_suggestion(self) -> None:
        try:
            log.info("Ctrl+Shift+F12 pressed: RESPOND TO SUGGESTION")
            self._publish("ui.respond_suggestion", {})
        except Exception as exc:
            log.exception(f"Unexpected error handling respond-suggestion: {exc}")


def start_hotkeys(
    event_bus: Optional[EventBus] = None,
    on_toggle: Optional[Callable[[bool], None]] = None,
) -> HotkeyListener:
    listener = HotkeyListener(event_bus=event_bus, on_toggle=on_toggle)
    listener.start()
    return listener


if __name__ == "__main__":
    import time

    log.info("Starting standalone hotkey test.")
    log.info("F12 toggles listening.")
    log.info("Ctrl+Shift+F10 toggles auto-reply.")
    log.info("Ctrl+Shift+F11 = respond now.")
    log.info("Ctrl+Shift+F12 = respond to suggestion.")
    listener = start_hotkeys(event_bus=None, on_toggle=None)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Standalone hotkey test stopped by user.")
