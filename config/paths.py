"""
paths.py
Central place where all file paths, folders, and directories are defined.
Ensures the entire system uses consistent paths.
"""

import os

# Base project directory (auto-detected)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Logs directory
LOG_DIR = os.path.join(BASE_DIR, "logs")

# Memory storage
MEMORY_DIR = os.path.join(BASE_DIR, "core", "memory", "storage")

# Temporary scratch area
TMP_DIR = os.path.join(BASE_DIR, "tmp")

# Ensure directories exist
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(MEMORY_DIR, exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)
