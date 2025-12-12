# core/hotkeys.py
from __future__ import annotations

from typing import Optional, Callable
import os
import threading

import keyboard  # Requires: pip install keyboard

from core.logger import get_logger
from core.event_bus import EventBus

log = get_logger("hotkeys")


def _env_hotkey(name: str, default: str) -> str:
    """
    Allows hotkey overrides without changing code.
    Example in .env:
      HOTKEY_LISTEN_TOGGLE=f12
      HOTKEY_AUTO_REPLY_TOGGLE=ctrl+shift+f10
      HOTKEY_RESPOND_NOW=ctrl+shift+f11
      HOTKEY_RESPOND_SUGGESTION=ctrl+shift+f12
    """
    val = os.getenv(name, "").strip()
    return val if val else default


HOTKEY_LISTEN_TOGGLE = _env_hotkey("HOTKEY_LISTEN_TOGGLE", "f12")
HOTKEY_AUTO_REPLY_TOGGLE = _env_hotkey("HOTKEY_AUTO_REPLY_TOGGLE", "ctrl+shift+f10")
HOTKEY_RESPOND_NOW = _env_hotkey("HOTKEY_RESPOND_NOW", "ctrl+shift+f11")
HOTKEY_RESPOND_SUGGESTION = _env_hotkey("HOTKEY_RESPOND_SUGGESTION", "ctrl+shift+f12")


class HotkeyListener:
    """
    Listens for global hotkeys and triggers actions.

    - F12 toggles "listening" state (True/False)
      Publishes: "voice.listen_toggle" with {"listening": bool}

    Stream permission gates (UI will mirror these later):
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
        self._registered: bool = False

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
        log.info("HotkeyListener thread started (F12 + Ctrl+Shift+F10/F11/F12).")  # matches current behavior :contentReference[oaicite:1]{index=1}

    def _run(self) -> None:
        log.info("Registering hotkeys.")

        # Prevent double-registering if start() is called twice accidentally
        if self._registered:
            log.warning("Hotkeys already registered; skipping re-register.")
            return
        self._registered = True

        # Keep existing behavior
        keyboard.add_hotkey(HOTKEY_LISTEN_TOGGLE, self._handle_listen_toggle)

        # Stream permission gates (safe combo: doesn't type into terminal)
        keyboard.add_hotkey(HOTKEY_AUTO_REPLY_TOGGLE, self._handle_toggle_auto_reply)
        keyboard.add_hotkey(HOTKEY_RESPOND_NOW, self._handle_respond_now)
        keyboard.add_hotkey(HOTKEY_RESPOND_SUGGESTION, self._handle_respond_suggestion)

        log.info("Hotkeys active: listen=%s auto_reply=%s now=%s suggestion=%s",
                 HOTKEY_LISTEN_TOGGLE, HOTKEY_AUTO_REPLY_TOGGLE, HOTKEY_RESPOND_NOW, HOTKEY_RESPOND_SUGGESTION)

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

    # ---- handlers ----

    def _handle_listen_toggle(self) -> None:
        try:
            self._listening = not self._listening
            state_label = "ON" if self._listening else "OFF"
            log.info(f"{HOTKEY_LISTEN_TOGGLE.upper()} pressed: toggling listening state to {state_label}")

            self._publish("voice.listen_toggle", {"listening": self._listening})

            if self._on_toggle is not None:
                try:
                    self._on_toggle(self._listening)
                except Exception as exc:
                    log.exception(f"Error calling on_toggle callback: {exc}")
        except Exception as exc:
            log.exception(f"Unexpected error handling listen toggle: {exc}")

    def _handle_toggle_auto_reply(self) -> None:
        try:
            self._auto_reply_enabled = not self._auto_reply_enabled
            state_label = "ON" if self._auto_reply_enabled else "OFF"
            log.info(f"{HOTKEY_AUTO_REPLY_TOGGLE.upper()} pressed: toggling AUTO-REPLY to {state_label}")  # current behavior :contentReference[oaicite:2]{index=2}

            self._publish("ui.auto_reply.set", {"enabled": self._auto_reply_enabled})
        except Exception as exc:
            log.exception(f"Unexpected error handling auto-reply toggle: {exc}")

    def _handle_respond_now(self) -> None:
        try:
            log.info(f"{HOTKEY_RESPOND_NOW.upper()} pressed: RESPOND NOW")  # current behavior :contentReference[oaicite:3]{index=3}
            self._publish("ui.respond_now", {})
        except Exception as exc:
            log.exception(f"Unexpected error handling respond-now: {exc}")

    def _handle_respond_suggestion(self) -> None:
        try:
            log.info(f"{HOTKEY_RESPOND_SUGGESTION.upper()} pressed: RESPOND TO SUGGESTION")  # current behavior :contentReference[oaicite:4]{index=4}
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
    log.info("Listen toggle: %s", HOTKEY_LISTEN_TOGGLE)
    log.info("Auto-reply toggle: %s", HOTKEY_AUTO_REPLY_TOGGLE)
    log.info("Respond now: %s", HOTKEY_RESPOND_NOW)
    log.info("Respond suggestion: %s", HOTKEY_RESPOND_SUGGESTION)
    listener = start_hotkeys(event_bus=None, on_toggle=None)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Standalone hotkey test stopped by user.")
