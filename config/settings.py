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
        f"online_enabled={ONLINE_FEATURES_ENABLED}"
    )
