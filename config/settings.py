"""
settings.py
Global runtime settings for the AI Co-Partner.
All toggles, flags, and tuning parameters live here.
"""

DEBUG = True
LOG_LEVEL = "INFO"

# Voice system settings
ENABLE_STT = True
ENABLE_TTS = True

# Vision system settings
ENABLE_VISION = False  # Will turn on when Kinect is connected

# Memory options
MEMORY_MAX_ITEMS = 5000
ENABLE_LONG_TERM_MEMORY = True

# Safety & security
SAFE_MODE = True
ALLOW_CODE_EXECUTION = False  # Locked down until explicitly enabled
