# core/hotkeys.py
"""
Global hotkeys (Windows-friendly) using `keyboard`.

Hotkeys:
- F12: toggle voice listening on/off  -> publishes 'voice.listen_toggle' with {'listening': bool}
- Ctrl+Shift+F10: toggle AUTO-REPLY   -> publishes 'ui.auto_reply.set' with {'enabled': bool}
- Ctrl+Shift+F11: respond now         -> publishes 'ui.respond_now' with {}
- Ctrl+Shift+F12: respond suggestion  -> publishes 'ui.respond_suggestion' with {}

Design notes:
- Uses combos that won't "type" into terminals.
- Safe if UI doesn't exist yet: events just go through EventBus.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Optional

try:
    import keyboard  # type: ignore
except Exception as e:  # pragma: no cover
    keyboard = None  # type: ignore
    _keyboard_import_error = e
else:
    _keyboard_import_error = None

log = logging.getLogger("hotkeys")


@dataclass
class HotkeyConfig:
    listen_toggle: str = "f12"
    auto_reply_toggle: str = "ctrl+shift+f10"
    respond_now: str = "ctrl+shift+f11"
    respond_suggestion: str = "ctrl+shift+f12"


class HotkeyListener:
    def __init__(self, event_bus, config: Optional[HotkeyConfig] = None):
        self.bus = event_bus
        self.cfg = config or HotkeyConfig()

        self._lock = threading.Lock()
        self._running = False
        self._listening = False
        self._auto_reply = False
        self._handles = []

    def start(self) -> None:
        if keyboard is None:
            raise RuntimeError(
                f"keyboard module not available. Install it with: pip install keyboard. Import error: {_keyboard_import_error}"
            )

        with self._lock:
            if self._running:
                return
            self._running = True

        # Register hotkeys
        self._handles.append(keyboard.add_hotkey(self.cfg.listen_toggle, self._on_listen_toggle))
        self._handles.append(keyboard.add_hotkey(self.cfg.auto_reply_toggle, self._on_auto_reply_toggle))
        self._handles.append(keyboard.add_hotkey(self.cfg.respond_now, self._on_respond_now))
        self._handles.append(keyboard.add_hotkey(self.cfg.respond_suggestion, self._on_respond_suggestion))

        log.info(
            "Hotkeys active: listen=%s auto_reply=%s now=%s suggestion=%s",
            self.cfg.listen_toggle,
            self.cfg.auto_reply_toggle,
            self.cfg.respond_now,
            self.cfg.respond_suggestion,
        )

    def stop(self) -> None:
        if keyboard is None:
            return

        with self._lock:
            if not self._running:
                return
            self._running = False

        # Unregister
        for h in self._handles:
            try:
                keyboard.remove_hotkey(h)
            except Exception:
                pass
        self._handles.clear()

    # ---- handlers ----

    def _on_listen_toggle(self) -> None:
        with self._lock:
            self._listening = not self._listening
            listening = self._listening
        log.info("F12 pressed: toggling listening state to %s", "ON" if listening else "OFF")
        self.bus.publish("voice.listen_toggle", {"listening": listening})

    def _on_auto_reply_toggle(self) -> None:
        with self._lock:
            self._auto_reply = not self._auto_reply
            enabled = self._auto_reply
        log.info("Ctrl+Shift+F10 pressed: toggling AUTO-REPLY to %s", "ON" if enabled else "OFF")
        self.bus.publish("ui.auto_reply.set", {"enabled": enabled})

    def _on_respond_now(self) -> None:
        log.info("Ctrl+Shift+F11 pressed: RESPOND NOW")
        self.bus.publish("ui.respond_now", {})

    def _on_respond_suggestion(self) -> None:
        log.info("Ctrl+Shift+F12 pressed: RESPOND TO SUGGESTION")
        self.bus.publish("ui.respond_suggestion", {})


_listener: Optional[HotkeyListener] = None


def start_hotkeys(event_bus, config: Optional[HotkeyConfig] = None) -> HotkeyListener:
    """
    Entry point used by core.main:
        from core.hotkeys import start_hotkeys
    """
    global _listener
    if _listener is None:
        _listener = HotkeyListener(event_bus, config=config)
        _listener.start()
        log.info("HotkeyListener thread started (F12 + Ctrl+Shift+F10/F11/F12).")
    return _listener


def stop_hotkeys() -> None:
    global _listener
    if _listener is not None:
        _listener.stop()
        _listener = None
