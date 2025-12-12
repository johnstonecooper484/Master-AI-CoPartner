"""config/settings.py

Global configuration and feature flags for the AI Co-Partner system.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

# Project root is two levels up: .../Master-AI-CoPartner/
PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]

# Central logs directory (used by logger module)
LOG_DIR: Path = PROJECT_ROOT / "logs"

# ---------------------------------------------------------
# Machine role
# ---------------------------------------------------------
# Tells the system which "brain" this machine is:
# - "main"         -> primary interaction machine
# - "vision_node"  -> camera / vision processing
# - "worker"       -> heavy tools / coding engine
#
# Override with env var AICOP_MACHINE_ROLE.

MACHINE_ROLE: str = os.getenv("AICOP_MACHINE_ROLE", "main").lower()

IS_MAIN: bool = MACHINE_ROLE == "main"
IS_VISION_NODE: bool = MACHINE_ROLE == "vision_node"
IS_WORKER: bool = MACHINE_ROLE == "worker"

# ---------------------------------------------------------
# Offline / online behavior
# ---------------------------------------------------------
# OFFLINE_ONLY:
#   True  -> only local / offline models
#   False -> allow online models when explicitly requested

OFFLINE_ONLY: bool = os.getenv("AICOP_OFFLINE_ONLY", "1") == "1"

MODE_OFFLINE_ONLY: str = "offline_only"
MODE_OFFLINE_WITH_ONLINE_BACKUP: str = "offline_with_online_backup"

ACTIVE_MODE: str = MODE_OFFLINE_ONLY if OFFLINE_ONLY else MODE_OFFLINE_WITH_ONLINE_BACKUP

# When can we use online models?
# We only allow online if:
#   - AICOP_ONLINE_ENABLED = "1"
#   - AND OPENAI_API_KEY is set
ONLINE_FEATURES_ENABLED: bool = (
    os.getenv("AICOP_ONLINE_ENABLED", "0") == "1"
    and bool(os.getenv("OPENAI_API_KEY"))
)

# ---------------------------------------------------------
# OpenAI / online model config (used only when online is allowed)
# ---------------------------------------------------------

OPENAI_MODEL_NAME: str = os.getenv("AICOP_OPENAI_MODEL", "gpt-4o-mini")

OPENAI_CHAT_COMPLETIONS_URL: str = os.getenv(
    "AICOP_OPENAI_URL",
    "https://api.openai.com/v1/chat/completions",
)

# ---------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------

LOG_LEVEL: str = os.getenv("AICOP_LOG_LEVEL", "INFO").upper()
LOG_MAX_BYTES: int = int(os.getenv("AICOP_LOG_MAX_BYTES", str(5 * 1024 * 1024)))
LOG_BACKUP_COUNT: int = int(os.getenv("AICOP_LOG_BACKUP_COUNT", "5"))

# ---------------------------------------------------------
# Voice / audio flags
# ---------------------------------------------------------
# These will matter when we hook up offline STT/TTS.
# For now they are simple switches we can read elsewhere.

VOICE_ENABLED: bool = os.getenv("AICOP_VOICE_ENABLED", "0") == "1"
STT_ENGINE: str = os.getenv("AICOP_STT_ENGINE", "offline")   # "offline" or "online"
TTS_ENGINE: str = os.getenv("AICOP_TTS_ENGINE", "offline")   # "offline" or "online"

# ---------------------------------------------------------
# Vision / camera flags (Logitech now, Kinect later)
# ---------------------------------------------------------

ACTIVE_CAMERA_DEVICE: str = "logitech_1080p_webcam"
USE_KINECT: bool = False  # future upgrade only

# ---------------------------------------------------------
# Vision / screen "eyes" flags (separate from voice)
# ---------------------------------------------------------
# These are SAFE defaults (OFF) and only matter if/when a module reads them.
# The goal: you can have:
# - voice on, vision off
# - vision on (watch), voice off
# - both on

VISION_ENABLED: bool = os.getenv("AICOP_VISION_ENABLED", "0") == "1"

# If VISION_ENABLED is on, should it start in watch mode by default?
VISION_WATCH_DEFAULT: bool = os.getenv("AICOP_VISION_WATCH_DEFAULT", "0") == "1"

# Default detail level for snapshots ("light" or "heavy")
VISION_DETAIL_DEFAULT: str = os.getenv("AICOP_VISION_DETAIL_DEFAULT", "light").lower()

# Save debug images when capturing (useful during dev; keep OFF for streaming safety)
VISION_SAVE_DEBUG_IMAGES: bool = os.getenv("AICOP_VISION_SAVE_DEBUG_IMAGES", "0") == "1"

# Optional region capture (e.g., chat box). Format: "x,y,w,h" (empty = full screen/monitor)
VISION_REGION: str = os.getenv("AICOP_VISION_REGION", "").strip()

# ---------------------------------------------------------
# UI / permissions (prep for Twitch auto-reply safety switch)
# ---------------------------------------------------------
# UI_AUTOREPLY_DEFAULT:
#   0 -> start OFF (safe)
#   1 -> start ON (only if you explicitly choose)
UI_AUTOREPLY_DEFAULT: bool = os.getenv("AICOP_UI_AUTOREPLY_DEFAULT", "0") == "1"

# ---------------------------------------------------------
# Utility
# ---------------------------------------------------------

def debug_dump() -> str:
    """
    Short summary of key settings for startup logging.
    """
    return (
        f"[settings] role={MACHINE_ROLE}, "
        f"offline_only={OFFLINE_ONLY}, "
        f"active_mode={ACTIVE_MODE}, "
        f"log_dir={LOG_DIR}, "
        f"log_level={LOG_LEVEL}, "
        f"voice_enabled={VOICE_ENABLED}, "
        f"stt_engine={STT_ENGINE}, "
        f"tts_engine={TTS_ENGINE}, "
        f"vision_enabled={VISION_ENABLED}, "
        f"vision_watch_default={VISION_WATCH_DEFAULT}, "
        f"vision_detail_default={VISION_DETAIL_DEFAULT}, "
        f"online_enabled={ONLINE_FEATURES_ENABLED}"
    )
