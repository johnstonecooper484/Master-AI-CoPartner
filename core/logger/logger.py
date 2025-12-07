"""
logger.py
Unified logging system for the AI Co-Partner.
Handles timestamped logs, levels, and rotation.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from config.paths import LOG_DIR


def get_logger(name: str) -> logging.Logger:
    """Returns a pre-configured logger instance."""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # Already configured

    logger.setLevel(logging.INFO)

    # Log file path
    log_path = os.path.join(LOG_DIR, f"{name}.log")

    # Rotating handler (1 MB per file, keep 5 backups)
    handler = RotatingFileHandler(
        log_path, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )

    formatter = logging.Formatter(
        "[%(asctime)s][%(levelname)s][%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
