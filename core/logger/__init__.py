"""
core/logger/__init__.py

Central logging helper for the AI Co-Partner system.

Usage:
    from core.logger import get_logger
    log = get_logger("core_manager")
    log.info("Something happened")
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import settings


def _ensure_log_dir() -> Path:
    """
    Make sure the log directory exists and return it.
    """
    log_dir: Path = settings.LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_logger(name: str, log_to_console: bool = True) -> logging.Logger:
    """
    Return a configured logger for the given name.

    - Writes to a rotating file in settings.LOG_DIR.
    - Optional console output.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        # Already configured
        return logger

    logger.setLevel(settings.LOG_LEVEL)

    log_dir = _ensure_log_dir()
    log_file = log_dir / f"{name}.log"

    # Rotating file handler
    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Prevent double logging to root logger
    logger.propagate = False

    return logger
