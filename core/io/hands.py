"""
core/io/hands.py

"HANDS" = safe, gated control of keyboard/mouse + app launching.
Default: DISABLED.

Goals:
- Allowlisted actions only (no arbitrary shell execution)
- Explicit enable gate (env var or code call)
- Confirmation required for risky actions (ex: close window)
- Strong audit log (JSONL) for every attempted action

This is intentionally conservative. We'll wire it into the IntentRouter/EventBus next.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    from core.logger import get_logger  # project logger
    log = get_logger("hands")
except Exception:
    log = logging.getLogger("hands")
    if not log.handlers:
        logging.basicConfig(level=logging.INFO)


class HandsError(RuntimeError):
    pass


def _now_iso() -> str:
    # simple, stable timestamp
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def _ensure_logs_dir() -> Path:
    p = Path("logs")
    p.mkdir(parents=True, exist_ok=True)
    return p


def _audit_write(event: Dict[str, Any]) -> None:
    """
    Append-only JSONL audit trail.
    """
    try:
        logs_dir = _ensure_logs_dir()
        path = logs_dir / "actions.log"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        log.exception("Failed to write actions audit log")


_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")


def _sanitize_text(text: str, max_len: int = 800) -> str:
    text = _CONTROL_CHARS.sub("", text)
    if len(text) > max_len:
        text = text[:max_len]
    return text


def _env_truthy(name: str, default: str = "0") -> bool:
    val = os.getenv(name, default).strip().lower()
    return val in {"1", "true", "yes", "y", "on"}


def _clamp_int(v: Any, lo: int, hi: int, default: int) -> int:
    try:
        iv = int(v)
    except Exception:
        return default
    if iv < lo:
        return lo
    if iv > hi:
        return hi
    return iv


def _get_foreground_window_info() -> Dict[str, Any]:
    """
    Best-effort foreground window info (Windows). No external deps.
    Returns:
      {"title": str, "pid": Optional[int], "process_name": str}
    """
    info = {"title": "", "pid": None, "process_name": ""}

    if os.name != "nt":
        return info

    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return info

        # title
        buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, buf, 512)
        info["title"] = buf.value or ""

        # pid
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        info["pid"] = int(pid.value) if pid.value else None

        # process name via QueryFullProcessImageNameW
        if pid.value:
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            hproc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
            if hproc:
                try:
                    size = wintypes.DWORD(1024)
                    path_buf = ctypes.create_unicode_buffer(1024)
                    ok = kernel32.QueryFullProcessImageNameW(hproc, 0, path_buf, ctypes.byref(size))
                    if ok:
                        exe_path = path_buf.value or ""
                        info["process_name"] = os.path.basename(exe_path).lower()
                finally:
                    kernel32.CloseHandle(hproc)

    except Exception:
        # silent degrade
        return info

    return info


@dataclass
class HandsConfig:
    enabled_env: str = "COPARTNER_HANDS_ENABLED"
    dry_run_env: str = "COPARTNER_HANDS_DRY_RUN"

    # safety limits
    max_type_chars: int = 800

    # built-in allowlist for launching apps (Windows-friendly)
    # (We can expand this later via config files.)
    allow_apps: Tuple[str, ...] = ("notepad", "explorer", "calc", "mspaint", "cmd")

    # close-window safety
    close_delay_ms_default: int = 1500  # give user time to alt-tab to the target window
    guarded_close_processes: Tuple[str, ...] = (
        "cmd.exe",
        "conhost.exe",
        "windowsterminal.exe",
        "wt.exe",
        "code.exe",
        "python.exe",
    )


class Hands:
    """
    Safe controller.

    Enable gate:
      - Set env COPARTNER_HANDS_ENABLED=1, OR
      - call hands.set_enabled(True)

    Dry-run:
      - Set env COPARTNER_HANDS_DRY_RUN=1
      - It will log actions but NOT execute them.
    """

    def __init__(self, cfg: Optional[HandsConfig] = None):
        self.cfg = cfg or HandsConfig()
        self._enabled = _env_truthy(self.cfg.enabled_env, "0")
        self._dry_run = _env_truthy(self.cfg.dry_run_env, "0")

        # Optional dependency for mouse automation
        self._pyautogui = None
        try:
            import pyautogui  # type: ignore
            self._pyautogui = pyautogui
            self._pyautogui.FAILSAFE = True
        except Exception:
            self._pyautogui = None

        log.info("Hands init: enabled=%s dry_run=%s pyautogui=%s",
                 self._enabled, self._dry_run, "yes" if self._pyautogui else "no")

    # --- gating ---

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)

    def set_dry_run(self, dry_run: bool) -> None:
        self._dry_run = bool(dry_run)

    def status(self) -> Dict[str, Any]:
        return {
            "enabled": self._enabled,
            "dry_run": self._dry_run,
            "mouse_backend": "pyautogui" if self._pyautogui else None,
            "allowed_apps": list(self.cfg.allow_apps),
        }

    def _require_enabled(self, action: str) -> None:
        if not self._enabled:
            raise HandsError(
                f"HANDS are disabled. Refusing action='{action}'. "
                f"Set {self.cfg.enabled_env}=1 to enable."
            )

    # --- public API ---

    def execute(self, action: Dict[str, Any], *, source: str = "unknown") -> Dict[str, Any]:
        """
        Execute a single action dict.

        Example:
          {"type":"open_app", "app":"notepad"}
          {"type":"type_text", "text":"hello"}
          {"type":"key_combo", "keys":"ctrl+s"}
          {"type":"click", "x":100, "y":200, "button":"left"}
          {"type":"close_window", "confirm": true, "delay_ms": 1500}
        """
        if not isinstance(action, dict):
            raise HandsError("Action must be a dict")

        a_type = str(action.get("type", "")).strip().lower()
        if not a_type:
            raise HandsError("Action missing 'type'")

        base_event = {
            "ts": _now_iso(),
            "source": source,
            "type": a_type,
            "dry_run": self._dry_run,
        }

        try:
            self._require_enabled(a_type)

            if a_type == "open_app":
                result = self._open_app(action)
            elif a_type == "type_text":
                result = self._type_text(action)
            elif a_type == "key_combo":
                result = self._key_combo(action)
            elif a_type == "click":
                result = self._click(action)
            elif a_type == "move_mouse":
                result = self._move_mouse(action)
            elif a_type == "close_window":
                result = self._close_window(action)
            else:
                raise HandsError(f"Unknown hands action type: {a_type}")

            _audit_write({**base_event, "ok": True, "details": result})
            return {"ok": True, "result": result}

        except Exception as exc:
            _audit_write({**base_event, "ok": False, "error": str(exc)})
            raise

    # --- implementations (allowlisted) ---

    def _open_app(self, action: Dict[str, Any]) -> Dict[str, Any]:
        app = str(action.get("app", "")).strip().lower()
        if not app:
            raise HandsError("open_app requires 'app'")

        if app not in self.cfg.allow_apps:
            raise HandsError(f"open_app blocked. app='{app}' not in allowlist: {self.cfg.allow_apps}")

        if self._dry_run:
            log.info("[DRY RUN] open_app: %s", app)
            return {"app": app, "started": False, "dry_run": True}

        cmd_map = {
            "notepad": ["notepad.exe"],
            "explorer": ["explorer.exe"],
            "calc": ["calc.exe"],
            "mspaint": ["mspaint.exe"],
            "cmd": ["cmd.exe"],
        }
        cmd = cmd_map.get(app)
        if not cmd:
            raise HandsError(f"No command mapping for app='{app}'")

        subprocess.Popen(cmd, shell=False)
        log.info("open_app: %s", app)
        return {"app": app, "started": True}

    def _type_text(self, action: Dict[str, Any]) -> Dict[str, Any]:
        text = action.get("text")
        if not isinstance(text, str) or not text:
            raise HandsError("type_text requires non-empty 'text'")

        text = _sanitize_text(text, max_len=self.cfg.max_type_chars)

        if self._dry_run:
            log.info("[DRY RUN] type_text: %r", text[:80])
            return {"typed_chars": len(text), "dry_run": True}

        if not self._pyautogui:
            raise HandsError("type_text requires pyautogui (pip install pyautogui)")

        self._pyautogui.typewrite(text, interval=0.0)
        return {"typed_chars": len(text)}

    def _key_combo(self, action: Dict[str, Any]) -> Dict[str, Any]:
        keys = str(action.get("keys", "")).strip().lower()
        if not keys:
            raise HandsError("key_combo requires 'keys' like 'ctrl+s'")

        if self._dry_run:
            log.info("[DRY RUN] key_combo: %s", keys)
            return {"keys": keys, "dry_run": True}

        try:
            import keyboard  # type: ignore
        except Exception:
            keyboard = None  # type: ignore

        if keyboard is not None:
            keyboard.send(keys)
            return {"keys": keys, "backend": "keyboard"}

        if not self._pyautogui:
            raise HandsError("key_combo requires keyboard or pyautogui")

        parts = [p.strip() for p in keys.split("+") if p.strip()]
        self._pyautogui.hotkey(*parts)
        return {"keys": keys, "backend": "pyautogui"}

    def _click(self, action: Dict[str, Any]) -> Dict[str, Any]:
        x = action.get("x")
        y = action.get("y")
        button = str(action.get("button", "left")).strip().lower()

        if not isinstance(x, int) or not isinstance(y, int):
            raise HandsError("click requires integer x and y")

        if button not in {"left", "right", "middle"}:
            raise HandsError("click button must be left/right/middle")

        if self._dry_run:
            log.info("[DRY RUN] click: (%s,%s) %s", x, y, button)
            return {"x": x, "y": y, "button": button, "dry_run": True}

        if not self._pyautogui:
            raise HandsError("click requires pyautogui (pip install pyautogui)")

        self._pyautogui.click(x=x, y=y, button=button)
        return {"x": x, "y": y, "button": button}

    def _move_mouse(self, action: Dict[str, Any]) -> Dict[str, Any]:
        x = action.get("x")
        y = action.get("y")
        duration = action.get("duration", 0.0)

        if not isinstance(x, int) or not isinstance(y, int):
            raise HandsError("move_mouse requires integer x and y")

        try:
            duration_f = float(duration)
        except Exception:
            duration_f = 0.0

        if duration_f < 0:
            duration_f = 0.0
        if duration_f > 5.0:
            duration_f = 5.0

        if self._dry_run:
            log.info("[DRY RUN] move_mouse: (%s,%s) duration=%s", x, y, duration_f)
            return {"x": x, "y": y, "duration": duration_f, "dry_run": True}

        if not self._pyautogui:
            raise HandsError("move_mouse requires pyautogui (pip install pyautogui)")

        self._pyautogui.moveTo(x=x, y=y, duration=duration_f)
        return {"x": x, "y": y, "duration": duration_f}

    def _close_window(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Risky. Requires confirm=True.
        Implementation: Alt+F4 (closes the active window).

        Safety:
        - default delay (ms) so user can alt-tab to the intended target
        - refuses to close guarded processes (cmd/vscode/python/etc) unless a future "force" is added
        """
        confirm = bool(action.get("confirm", False))
        if not confirm:
            raise HandsError("close_window requires confirm=True (safety)")

        if self._dry_run:
            log.info("[DRY RUN] close_window (alt+f4)")
            return {"closed": False, "dry_run": True}

        delay_ms = _clamp_int(
            action.get("delay_ms", self.cfg.close_delay_ms_default),
            lo=0,
            hi=5000,
            default=self.cfg.close_delay_ms_default,
        )

        if delay_ms > 0:
            log.info("close_window: waiting %sms for user to focus target window...", delay_ms)
            time.sleep(delay_ms / 1000.0)

        fg = _get_foreground_window_info()
        proc = (fg.get("process_name") or "").lower()
        title = fg.get("title") or ""

        if proc and proc in set(self.cfg.guarded_close_processes):
            raise HandsError(
                f"Refusing to close protected window: process='{proc}' title='{title}'. "
                f"Alt+Tab to the intended app and try again."
            )

        try:
            import keyboard  # type: ignore
            keyboard.send("alt+f4")
            return {"closed": True, "method": "keyboard", "target_process": proc, "target_title": title}
        except Exception:
            pass

        if not self._pyautogui:
            raise HandsError("close_window requires keyboard or pyautogui")

        self._pyautogui.hotkey("alt", "f4")
        return {"closed": True, "method": "pyautogui", "target_process": proc, "target_title": title}
