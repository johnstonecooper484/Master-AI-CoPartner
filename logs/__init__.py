"""
core/logger/__init__.py

Provides LoggerManager and get_logger for the entire system.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


# Where logs will be stored: ./logs/
BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def _build_logger(name: str) -> logging.Logger:
    """
    Create or return a logger with a rotating file handler.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    log_file = LOG_DIR / f"{name}.log"
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
    logger.propagate = False

    return logger


class LoggerManager:
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        return _build_logger(name)


def get_logger(name: str) -> logging.Logger:
    return LoggerManager.get_logger(name)
