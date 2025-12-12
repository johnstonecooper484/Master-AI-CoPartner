# core/io/vision.py
"""
Vision (screen) module — local-first.

Blueprint rules enforced:
- Watch Mode is OFF by default.
- When Watch Mode is ON, we capture frames at a controlled rate.
- No automatic memory writes. Ever.
- Debug screenshots (optional) go to tmp/vision/.
- Designed to be portable later (ThinkStation A can replace the provider).

This module only produces "VisionSnapshot" data for downstream grounding.
"""

from __future__ import annotations

import os
import time
import threading
import datetime as _dt
from dataclasses import dataclass, asdict
from typing import Any, Callable, Dict, Optional, Tuple

# Optional dependencies (degraded mode if missing)
_MSS_AVAILABLE = False
_PIL_AVAILABLE = False
_WIN32_AVAILABLE = False
_PSUTIL_AVAILABLE = False

try:
    import mss  # type: ignore
    import mss.tools  # type: ignore
    _MSS_AVAILABLE = True
except Exception:
    _MSS_AVAILABLE = False

try:
    from PIL import ImageGrab  # type: ignore
    _PIL_AVAILABLE = True
except Exception:
    _PIL_AVAILABLE = False

try:
    import win32gui  # type: ignore
    import win32process  # type: ignore
    _WIN32_AVAILABLE = True
except Exception:
    _WIN32_AVAILABLE = False

try:
    import psutil  # type: ignore
    _PSUTIL_AVAILABLE = True
except Exception:
    _PSUTIL_AVAILABLE = False


# ---- Logging ----
import logging
log = logging.getLogger("vision")


# ---- Types ----
Region = Tuple[int, int, int, int]  # (left, top, width, height)


@dataclass
class VisionSnapshot:
    ts: str
    watch_mode: bool
    detail: str

    # focus / context
    active_window_title: str
    active_process_name: str
    active_pid: Optional[int]

    # capture info
    capture_method: str
    region: Optional[Region]
    image_path: Optional[str]
    width: Optional[int]
    height: Optional[int]

    # grounding helpers
    notes: str
    warnings: list[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---- Internal state ----
_watch_lock = threading.Lock()
_watch_thread: Optional[threading.Thread] = None
_watch_stop = threading.Event()

_watch_enabled: bool = False
_watch_detail: str = "light"  # "light" or "detailed"
_watch_fps: float = 2.0  # default: 2 frames/sec
_watch_region: Optional[Region] = None
_watch_save_debug_images: bool = True

_last_focus_signature: str = ""


def _ensure_tmp_vision_dir() -> str:
    path = os.path.join("tmp", "vision")
    os.makedirs(path, exist_ok=True)
    return path


def _now_iso() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


# ---- Active window detection ----
def get_active_window() -> Dict[str, Any]:
    """
    Returns:
      {
        "title": str,
        "pid": Optional[int],
        "process_name": str,
        "warnings": list[str],
      }
    Degraded mode: may return title only.
    """
    title = ""
    pid: Optional[int] = None
    proc_name = ""

    warnings: list[str] = []

    if _WIN32_AVAILABLE:
        try:
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd) or ""
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
        except Exception as e:
            warnings.append(f"win32 active window failed: {e!r}")
    else:
        warnings.append("pywin32 not available (install pywin32 for best active-window detection).")

    if pid is not None and _PSUTIL_AVAILABLE:
        try:
            proc = psutil.Process(pid)
            proc_name = proc.name()
        except Exception as e:
            warnings.append(f"psutil process name failed: {e!r}")
    elif pid is not None and not _PSUTIL_AVAILABLE:
        warnings.append("psutil not available (install psutil to get process names).")

    return {
        "title": title,
        "pid": pid,
        "process_name": proc_name,
        "warnings": warnings,
    }


# ---- Screen capture ----
def capture_screen(
    region: Optional[Region] = None,
    save_debug_image: bool = True,
) -> Dict[str, Any]:
    """
    Captures the screen (full screen or region). Returns:
      {
        "image_path": Optional[str],
        "width": Optional[int],
        "height": Optional[int],
        "method": str,
        "warnings": list[str],
      }

    Notes:
    - Uses mss if available (fast).
    - Falls back to PIL.ImageGrab if available.
    - If neither exists, returns degraded info with warnings.
    """
    warnings: list[str] = []
    tmp_dir = _ensure_tmp_vision_dir()
    image_path: Optional[str] = None
    w: Optional[int] = None
    h: Optional[int] = None

    # Prefer MSS
    if _MSS_AVAILABLE:
        try:
            with mss.mss() as sct:
                if region is None:
                    mon = sct.monitors[1]  # PRIMARY monitor only
                    left, top, width, height = mon["left"], mon["top"], mon["width"], mon["height"]
                else:
                    left, top, width, height = region

                grab = sct.grab({"left": left, "top": top, "width": width, "height": height})
                w, h = grab.width, grab.height

                if save_debug_image:
                    ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
                    image_path = os.path.join(tmp_dir, f"screen_{ts}.png")
                    mss.tools.to_png(grab.rgb, grab.size, output=image_path)

            return {
                "image_path": image_path,
                "width": w,
                "height": h,
                "method": "mss",
                "warnings": warnings,
            }
        except Exception as e:
            warnings.append(f"mss capture failed: {e!r}")

    # Fallback: PIL ImageGrab
    if _PIL_AVAILABLE:
        try:
            bbox = None
            if region is not None:
                left, top, width, height = region
                bbox = (left, top, left + width, top + height)

            img = ImageGrab.grab(bbox=bbox)
            w, h = img.size

            if save_debug_image:
                ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
                image_path = os.path.join(tmp_dir, f"screen_{ts}.png")
                img.save(image_path)

            return {
                "image_path": image_path,
                "width": w,
                "height": h,
                "method": "pil_imagegrab",
                "warnings": warnings,
            }
        except Exception as e:
            warnings.append(f"PIL ImageGrab capture failed: {e!r}")

    warnings.append("No capture backend available. Install 'mss' (recommended) or 'Pillow'.")
    return {
        "image_path": None,
        "width": None,
        "height": None,
        "method": "none",
        "warnings": warnings,
    }


# ---- Snapshot building (ground truth producer) ----
def build_snapshot(
    detail: str = "light",
    region: Optional[Region] = None,
    capture: bool = True,
    save_debug_image: bool = True,
) -> VisionSnapshot:
    """
    Creates a VisionSnapshot.
    - detail="light": focus + optional screenshot
    - detail="detailed": same now (OCR comes later), but we mark the intent
    """
    focus = get_active_window()
    warnings = list(focus.get("warnings", []))

    cap_method = "none"
    image_path = None
    width = None
    height = None

    if capture:
        cap = capture_screen(region=region, save_debug_image=save_debug_image)
        cap_method = cap["method"]
        image_path = cap["image_path"]
        width = cap["width"]
        height = cap["height"]
        warnings.extend(cap.get("warnings", []))

    notes = ""
    if not focus.get("title") and not focus.get("process_name"):
        notes = "Active window info is limited (install pywin32 + psutil for best results)."

    return VisionSnapshot(
        ts=_now_iso(),
        watch_mode=is_watching(),
        detail=detail,
        active_window_title=focus.get("title", "") or "",
        active_process_name=focus.get("process_name", "") or "",
        active_pid=focus.get("pid", None),
        capture_method=cap_method,
        region=region,
        image_path=image_path,
        width=width,
        height=height,
        notes=notes,
        warnings=warnings,
    )


# ---- Watch Mode loop ----
def start_watch(
    callback: Callable[[VisionSnapshot], None],
    fps: float = 2.0,
    detail: str = "light",
    region: Optional[Region] = None,
    save_debug_images: bool = True,
) -> None:
    """
    Starts Watch Mode in a background thread.
    - callback(snapshot) called on each cycle (or when focus changes, depending on detail).
    - fps is clamped to safe range.
    """
    global _watch_thread, _watch_enabled, _watch_fps, _watch_detail, _watch_region, _watch_save_debug_images

    if fps <= 0:
        fps = 1.0
    fps = max(0.5, min(float(fps), 5.0))  # safe clamp: 0.5 to 5 FPS

    detail = (detail or "light").strip().lower()
    if detail not in ("light", "detailed"):
        detail = "light"

    with _watch_lock:
        if _watch_thread and _watch_thread.is_alive():
            log.info("Watch mode already running.")
            return

        _watch_enabled = True
        _watch_fps = fps
        _watch_detail = detail
        _watch_region = region
        _watch_save_debug_images = bool(save_debug_images)

        _watch_stop.clear()

        _watch_thread = threading.Thread(
            target=_watch_loop,
            args=(callback,),
            name="VisionWatchLoop",
            daemon=True,
        )
        _watch_thread.start()

    log.info("Watch mode started (fps=%.2f, detail=%s).", _watch_fps, _watch_detail)


def stop_watch() -> None:
    """Stops Watch Mode."""
    global _watch_enabled
    with _watch_lock:
        _watch_enabled = False
        _watch_stop.set()

    log.info("Watch mode stop requested.")


def is_watching() -> bool:
    with _watch_lock:
        t = _watch_thread
        return bool(t and t.is_alive() and _watch_enabled)


def _watch_loop(callback: Callable[[VisionSnapshot], None]) -> None:
    """
    Loop policy:
    - Always gathers active window info.
    - Captures a screenshot:
        - every cycle in "detailed"
        - or only when focus changes in "light" (saves CPU)
    """
    global _last_focus_signature

    interval = 1.0 / max(_watch_fps, 0.5)

    while not _watch_stop.is_set():
        try:
            focus = get_active_window()
            title = focus.get("title", "") or ""
            proc = focus.get("process_name", "") or ""
            pid = focus.get("pid", None)

            focus_sig = f"{pid}|{proc}|{title}"

            capture = False
            if _watch_detail == "detailed":
                capture = True
            else:
                capture = (focus_sig != _last_focus_signature)

            snap = build_snapshot(
                detail=_watch_detail,
                region=_watch_region,
                capture=capture,
                save_debug_image=_watch_save_debug_images,
            )

            _last_focus_signature = focus_sig
            callback(snap)

        except Exception as e:
            log.exception("Vision watch loop error: %r", e)

        time.sleep(interval)


# ---- Convenience: "describe block" generator (ground truth text) ----
def describe_snapshot(snapshot: VisionSnapshot) -> str:
    """
    Produces a plaintext description for "describe then answer" grounding.
    Downstream code should:
      1) show this block
      2) answer using only this block
    """
    lines = []
    lines.append(f"[Vision Snapshot @ {snapshot.ts}]")
    lines.append(f"Watch Mode: {'ON' if snapshot.watch_mode else 'OFF'} | Detail: {snapshot.detail}")
    lines.append(f"Active App: {snapshot.active_process_name or '(unknown)'}")
    lines.append(f"Window Title: {snapshot.active_window_title or '(unknown)'}")
    lines.append(f"Capture: {snapshot.capture_method} | Image: {snapshot.image_path or '(none)'}")
    if snapshot.region:
        lines.append(
            f"Region: left={snapshot.region[0]} top={snapshot.region[1]} w={snapshot.region[2]} h={snapshot.region[3]}"
        )
    if snapshot.width and snapshot.height:
        lines.append(f"Image Size: {snapshot.width}x{snapshot.height}")
    if snapshot.notes:
        lines.append(f"Notes: {snapshot.notes}")
    if snapshot.warnings:
        lines.append("Warnings:")
        for w in snapshot.warnings[:8]:
            lines.append(f"- {w}")
        if len(snapshot.warnings) > 8:
            lines.append(f"- (+{len(snapshot.warnings) - 8} more)")
    return "\n".join(lines)
