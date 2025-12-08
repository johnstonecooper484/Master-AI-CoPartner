"""
core/main.py

Entry point for the Master AI Co-Partner system.

Right now this:
- Loads global settings
- Initializes logging
- Logs a startup summary
- Chooses behavior based on MACHINE_ROLE (main / vision_node / worker)

Later, this will:
- Start the main event loop
- Wire in voice, camera, task engine, etc.
"""

from __future__ import annotations

from config import settings
from core.logger import get_logger


log = get_logger("core_main")


def run_main_role() -> None:
    """
    Behavior for the MAIN machine (primary interaction node).
    For now, just a placeholder with clear logging.
    """
    log.info("Running in MAIN role (primary interaction node).")
    # TODO: hook up:
    # - Voice I/O
    # - Command router
    # - UI / hotkeys
    # - Task engine entry point


def run_vision_role() -> None:
    """
    Behavior for the VISION_NODE machine.
    """
    log.info("Running in VISION_NODE role (camera / vision processing).")
    # TODO: hook up:
    # - Webcam/Kinect capture
    # - Frame processing
    # - Event bus publishing


def run_worker_role() -> None:
    """
    Behavior for the WORKER machine.
    """
    log.info("Running in WORKER role (heavy tools / coding engine).")
    # TODO: hook up:
    # - Code assistant backend
    # - Heavy jobs
    # - Integrations


def main() -> None:
    """
    Main entry point for the AI Co-Partner.

    This should be the ONLY place that decides what to start
    based on the machine role.
    """
    log.info("=== Master AI Co-Partner starting up ===")
    log.info(settings.debug_dump())

    try:
        if settings.IS_MAIN:
            run_main_role()
        elif settings.IS_VISION_NODE:
            run_vision_role()
        elif settings.IS_WORKER:
            run_worker_role()
        else:
            log.error(f"Unknown MACHINE_ROLE: {settings.MACHINE_ROLE!r}")
    except Exception as exc:
        log.exception(f"Fatal error in main(): {exc}")
        raise
    finally:
        log.info("=== Master AI Co-Partner shutdown ===")


if __name__ == "__main__":
    main()
