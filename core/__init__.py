# core/logger/__init__.py

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os

from config.paths import LOG_DIR

# Cache of created loggers
_loggers: dict[str, logging.Logger] = {}


def _build_logger(name: str) -> logging.Logger:
    """Create a rotating file logger for the given name."""
    logger = logging.getLogger(name)

    # If we've already built this logger, just return it
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # LOG_DIR is a string from config.paths
    log_file = os.path.join(LOG_DIR, f"{name}.log")

    handler = RotatingFileHandler(
        log_file,
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Also log to console
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Main entry point: from core.logger import get_logger
    """
    if name not in _loggers:
        _loggers[name] = _build_logger(name)
    return _loggers[name]
