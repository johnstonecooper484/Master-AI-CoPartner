# core/command_handler.py

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger("ai_copartner.command_handler")


@dataclass
class CommandResult:
    """Simple result object for commands."""
    status: str
    message: str
    data: Dict[str, Any] | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "data": self.data or {},
        }


class CommandHandler:
    """
    Central place where all high-level commands funnel through.

    Later:
    - Voice input will call handle_command(...)
    - UI / hotkeys can also call handle_command(...)
    - Security can inspect commands here in one place
    """

    def __init__(self) -> None:
        logger.info("CommandHandler initialized")

        # In the future, this can be dynamic:
        # - loaded from config
        # - extended by plugins / skills
        self._built_in_commands = {
            "ping": self._cmd_ping,
            "help": self._cmd_help,
        }

    def handle_command(
        self,
        raw_command: str,
        source: str = "cli",
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point.

        raw_command: what the user said/typed
        source: 'cli', 'voice', 'discord', etc.
        session_id: optional tracking id
        """
        logger.info(
            "Incoming command",
            extra={
                "raw_command": raw_command,
                "source": source,
                "session_id": session_id,
            },
        )

        if not raw_command or not raw_command.strip():
            return CommandResult(
                status="error",
                message="Empty command",
            ).to_dict()

        cmd = raw_command.strip().lower()

        # For now we only handle a tiny core set
        handler = self._built_in_commands.get(cmd)
        if handler is None:
            logger.warning("Unknown command: %s", cmd)
            return CommandResult(
                status="unknown_command",
                message=f"Unknown command: {cmd}",
            ).to_dict()

        try:
            return handler(cmd).to_dict()
        except Exception as exc:
            # Keep this very defensive: never let a crash bubble out
            logger.exception("Error while handling command %r: %s", cmd, exc)
            return CommandResult(
                status="error",
                message="Command failed internally",
            ).to_dict()

    # ── Built-in commands ──────────────────────────────────────────────

    def _cmd_ping(self, cmd: str) -> CommandResult:
        """Basic health check: used by tests and watchdogs."""
        logger.debug("Handling ping command")
        return CommandResult(
            status="ok",
            message="pong",
            data={"command": cmd},
        )

    def _cmd_help(self, cmd: str) -> CommandResult:
        """Return a tiny help list. We’ll expand this later."""
        logger.debug("Handling help command")
        return CommandResult(
            status="ok",
            message="Available commands: ping, help",
            data={"commands": sorted(self._built_in_commands.keys())},
        )
