# core/hotkeys.py
"""
Global hotkeys (Windows-friendly) using `keyboard`.

Hotkeys:
- F12: toggle voice listening on/off        -> publishes 'voice.listen_toggle' with {'listening': bool}
- Ctrl+Shift+F10: toggle AUTO-REPLY         -> publishes 'ui.auto_reply.set' with {'enabled': bool}
- Ctrl+Shift+F11: respond now               -> publishes 'ui.respond_now' with {}
- Ctrl+Shift+F12: respond suggestion        -> publishes 'ui.respond_suggestion' with {}

Vision hotkeys:
- Ctrl+Shift+F7: toggle Vision->Memory gate -> publishes 'vision.memory.set' with {'allowed': bool}
- Ctrl+Shift+F8: toggle Vision Watch Mode   -> publishes 'vision.watch.set' with {'enabled': bool}
- Ctrl+Shift+F9: Describe Now (one-shot)    -> publishes 'vision.describe_now' with {'image_path': str | None}

Watch Mode behavior (important):
- Default is "detailed" at 1 FPS, meaning it captures once per second even if the active window does not change.
- You can tune it without editing code:
    COPARTNER_VISION_WATCH_DETAIL=light|detailed
    COPARTNER_VISION_WATCH_FPS=1.0 (try 2.0 later, but note: higher FPS will create more files)

Design notes:
- Uses combos that won't "type" into terminals.
- Safe if UI doesn't exist yet: events just go through EventBus.
- Vision actions are wired to core.io.vision directly so they work immediately.
"""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from typing import Optional, Any, Dict

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

    # Vision controls (safe + terminal-friendly)
    vision_memory_toggle: str = "ctrl+shift+f7"
    vision_watch_toggle: str = "ctrl+shift+f8"
    vision_describe_now: str = "ctrl+shift+f9"


def _get_watch_detail() -> str:
    val = (os.getenv("COPARTNER_VISION_WATCH_DETAIL", "detailed") or "detailed").strip().lower()
    # vision.py treats anything other than "detailed" as focus-change mode, so keep it strict.
    return "detailed" if val == "detailed" else "light"


def _get_watch_fps() -> float:
    raw = os.getenv("COPARTNER_VISION_WATCH_FPS", "1.0")
    try:
        fps = float(raw)
    except Exception:
        fps = 1.0
    # sane clamp
    if fps < 0.5:
        fps = 0.5
    if fps > 10.0:
        fps = 10.0
    return fps


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

        # Vision hotkeys
        self._handles.append(keyboard.add_hotkey(self.cfg.vision_memory_toggle, self._on_vision_memory_toggle))
        self._handles.append(keyboard.add_hotkey(self.cfg.vision_watch_toggle, self._on_vision_watch_toggle))
        self._handles.append(keyboard.add_hotkey(self.cfg.vision_describe_now, self._on_vision_describe_now))

        log.info(
            "Hotkeys active: listen=%s auto_reply=%s now=%s suggestion=%s | vision_mem=%s vision_watch=%s vision_describe=%s",
            self.cfg.listen_toggle,
            self.cfg.auto_reply_toggle,
            self.cfg.respond_now,
            self.cfg.respond_suggestion,
            self.cfg.vision_memory_toggle,
            self.cfg.vision_watch_toggle,
            self.cfg.vision_describe_now,
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

    # ---- vision helpers ----

    def _publish_vision_snapshot(self, snap: Any, source: str) -> None:
        """
        Best-effort serialization for EventBus consumers.
        """
        payload: Dict[str, Any] = {
            "source": source,
            "image_path": getattr(snap, "image_path", None),
            "capture_method": getattr(snap, "capture_method", None),
            "ts": getattr(snap, "ts", None),
            "detail": getattr(snap, "detail", None),
            "active_window_title": getattr(snap, "active_window_title", None),
            "active_process_name": getattr(snap, "active_process_name", None),
            "active_pid": getattr(snap, "active_pid", None),
        }
        try:
            self.bus.publish("vision.snapshot", payload)
        except Exception:
            log.exception("Failed to publish vision.snapshot event")

    # ---- vision handlers ----

    def _on_vision_memory_toggle(self) -> None:
        try:
            from core.io import vision  # lazy import to avoid cycles
            allowed = bool(vision.toggle_vision_memory_allowed())
            log.info("Ctrl+Shift+F7 pressed: Vision->Memory permission %s", "ON" if allowed else "OFF")
            self.bus.publish("vision.memory.set", {"allowed": allowed})
        except Exception:
            log.exception("Vision->Memory toggle failed")
            try:
                self.bus.publish("vision.error", {"where": "vision_memory_toggle"})
            except Exception:
                pass

    def _on_vision_watch_toggle(self) -> None:
        try:
            from core.io import vision  # lazy import to avoid cycles

            if vision.is_watching():
                vision.stop_watch()
                enabled = False
            else:
                detail = _get_watch_detail()
                fps = _get_watch_fps()

                # Publish snapshots so other subsystems can subscribe later.
                def _cb(snap: Any) -> None:
                    self._publish_vision_snapshot(snap, source="watch")

                vision.start_watch(
                    callback=_cb,
                    fps=fps,
                    detail=detail,          # <-- key change: default detailed captures even without focus change
                    region=None,
                    save_debug_images=True,
                )
                enabled = True

            log.info("Ctrl+Shift+F8 pressed: Vision Watch Mode %s", "ON" if enabled else "OFF")
            self.bus.publish("vision.watch.set", {"enabled": enabled})
        except Exception:
            log.exception("Vision watch toggle failed")
            try:
                self.bus.publish("vision.error", {"where": "vision_watch_toggle"})
            except Exception:
                pass

    def _on_vision_describe_now(self) -> None:
        try:
            from core.io import vision  # lazy import to avoid cycles

            snap = vision.describe_now(detail="light", region=None, save_debug_image=True)
            image_path = getattr(snap, "image_path", None)
            log.info("Ctrl+Shift+F9 pressed: Describe Now captured %s", image_path or "(no image_path)")
            self.bus.publish("vision.describe_now", {"image_path": image_path})
            self._publish_vision_snapshot(snap, source="describe_now")
        except Exception:
            log.exception("Describe Now failed")
            try:
                self.bus.publish("vision.error", {"where": "vision_describe_now"})
            except Exception:
                pass


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
        log.info("HotkeyListener active (F12 + Ctrl+Shift+F10/F11/F12/F7/F8/F9).")
    return _listener


def stop_hotkeys() -> None:
    global _listener
    if _listener is not None:
        _listener.stop()
        _listener = None
