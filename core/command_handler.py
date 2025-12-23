# core/command_handler.py

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("ai_copartner.command_handler")


# ------------------------------------------------------------
# Permission tiers (simple + explicit)
# ------------------------------------------------------------

ROLE_EVERYONE = "everyone"
ROLE_SUBSCRIBER = "subscriber"
ROLE_VIP = "vip"
ROLE_MODERATOR = "moderator"
ROLE_BROADCASTER = "broadcaster"

ROLE_ORDER = {
    ROLE_EVERYONE: 0,
    ROLE_SUBSCRIBER: 1,
    ROLE_VIP: 2,
    ROLE_MODERATOR: 3,
    ROLE_BROADCASTER: 4,
}


def _norm_role(role: str) -> str:
    r = (role or "").strip().lower()
    return r if r in ROLE_ORDER else ROLE_EVERYONE


def _role_allows(user_role: str, required_role: str) -> bool:
    u = ROLE_ORDER.get(_norm_role(user_role), 0)
    req = ROLE_ORDER.get(_norm_role(required_role), 0)
    return u >= req


# ------------------------------------------------------------
# Data models
# ------------------------------------------------------------

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


@dataclass
class CommandDefinition:
    name: str
    response: str
    permission: str = ROLE_EVERYONE
    cooldown_seconds: float = 3.0          # global per-command cooldown
    user_cooldown_seconds: float = 10.0    # per-user cooldown for this command
    enabled: bool = True


# ------------------------------------------------------------
# Command Handler
# ------------------------------------------------------------

class CommandHandler:
    """
    Central place where all high-level commands funnel through.

    Now supports:
    - Built-in core commands (ping/help)
    - Chat-style commands: !command
    - Permission tiers
    - Cooldowns (global + per-user)
    - Optional JSON config loading (safe if missing)
    """

    def __init__(self, commands_path: Optional[str | Path] = None) -> None:
        logger.info("CommandHandler initialized")

        # Built-ins (always available)
        self._built_in_commands = {
            "ping": self._cmd_ping,
            "help": self._cmd_help,
        }

        # Custom commands (loaded from file if present)
        self._custom_commands: Dict[str, CommandDefinition] = {}

        # Cooldown tracking
        self._last_used_global: Dict[str, float] = {}
        self._last_used_user: Dict[Tuple[str, str], float] = {}  # (command, user) -> ts

        # Optional custom commands config
        self._commands_path = Path(commands_path) if commands_path else self._default_commands_path()
        self.reload_custom_commands()

    # ---------------------------------------------------------
    # Paths / Loading
    # ---------------------------------------------------------

    def _default_commands_path(self) -> Path:
        """
        Safe default location. If it doesn't exist, nothing breaks.
        You can change this later to match your final project tree.
        """
        # Try to anchor to project root: .../Master-AI-CoPartner/
        # This file is typically: <root>/core/command_handler.py
        root = Path(__file__).resolve().parents[1]
        return root / "data" / "skills" / "streaming" / "commands.json"

    def reload_custom_commands(self) -> None:
        """
        Load commands from JSON if available.
        Format:
        {
          "hello": {"response":"Hi!", "permission":"everyone", "cooldown_seconds":3, "user_cooldown_seconds":10, "enabled":true},
          "so": {"response":"Shoutout @{{user}}", "permission":"moderator"}
        }
        """
        path = self._commands_path
        self._custom_commands = {}

        if not path.exists():
            logger.info("Custom commands file not found (ok): %s", path)
            return

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("commands.json must be a JSON object at top level")

            loaded = 0
            for name, cfg in raw.items():
                if not isinstance(name, str):
                    continue
                if not isinstance(cfg, dict):
                    continue

                cmd_name = name.strip().lower().lstrip("!")
                if not cmd_name:
                    continue

                response = str(cfg.get("response", "")).strip()
                if not response:
                    continue

                cd = CommandDefinition(
                    name=cmd_name,
                    response=response,
                    permission=_norm_role(str(cfg.get("permission", ROLE_EVERYONE))),
                    cooldown_seconds=float(cfg.get("cooldown_seconds", 3.0) or 3.0),
                    user_cooldown_seconds=float(cfg.get("user_cooldown_seconds", 10.0) or 10.0),
                    enabled=bool(cfg.get("enabled", True)),
                )
                self._custom_commands[cmd_name] = cd
                loaded += 1

            logger.info("Loaded %d custom commands from %s", loaded, path)

        except Exception as exc:
            logger.exception("Failed to load custom commands from %s: %s", path, exc)

    # ---------------------------------------------------------
    # Core CLI-style handling (existing)
    # ---------------------------------------------------------

    def handle_command(
        self,
        raw_command: str,
        source: str = "cli",
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Legacy/CLI command handler: exact matches like 'ping', 'help'.
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
            return CommandResult(status="error", message="Empty command").to_dict()

        cmd = raw_command.strip().lower()

        handler = self._built_in_commands.get(cmd)
        if handler is None:
            logger.warning("Unknown command: %s", cmd)
            return CommandResult(status="unknown_command", message=f"Unknown command: {cmd}").to_dict()

        try:
            return handler(cmd).to_dict()
        except Exception as exc:
            logger.exception("Error while handling command %r: %s", cmd, exc)
            return CommandResult(status="error", message="Command failed internally").to_dict()

    # ---------------------------------------------------------
    # Chat-style handling (NEW)
    # ---------------------------------------------------------

    def handle_chat_message(
        self,
        text: str,
        *,
        user: str,
        role: str = ROLE_EVERYONE,
        source: str = "chat",
    ) -> Optional[Dict[str, Any]]:
        """
        Chat command entry:
          - Only triggers if message starts with '!'
          - Enforces permissions + cooldowns
          - Returns a CommandResult dict or None if not a command
        """
        msg = (text or "").strip()
        if not msg.startswith("!"):
            return None

        name, args = self._parse_bang_command(msg)
        if not name:
            return CommandResult(status="error", message="Empty command name").to_dict()

        # Built-ins via !ping / !help as well
        if name in self._built_in_commands:
            try:
                return self._built_in_commands[name](name).to_dict()
            except Exception:
                logger.exception("Built-in chat command failed: %s", name)
                return CommandResult(status="error", message="Command failed internally").to_dict()

        cmd = self._custom_commands.get(name)
        if cmd is None:
            return CommandResult(status="unknown_command", message=f"Unknown command: !{name}").to_dict()

        if not cmd.enabled:
            return CommandResult(status="disabled", message=f"Command disabled: !{name}").to_dict()

        user_role = _norm_role(role)
        if not _role_allows(user_role, cmd.permission):
            logger.info(
                "Blocked command by permission",
                extra={"cmd": name, "user": user, "role": user_role, "required": cmd.permission, "source": source},
            )
            return CommandResult(status="blocked", message="Not allowed for your role").to_dict()

        # Cooldowns
        now = time.time()
        ok, wait = self._check_cooldowns(name, user, now, cmd.cooldown_seconds, cmd.user_cooldown_seconds)
        if not ok:
            return CommandResult(
                status="cooldown",
                message=f"Cooldown active. Try again in {wait:.1f}s",
                data={"retry_after_seconds": round(wait, 1)},
            ).to_dict()

        # Mark usage
        self._mark_used(name, user, now)

        # Render response (simple templating)
        rendered = self._render_response(cmd.response, user=user, args=args)

        logger.info(
            "Command executed",
            extra={"cmd": name, "user": user, "role": user_role, "source": source},
        )

        return CommandResult(
            status="ok",
            message=rendered,
            data={"command": name},
        ).to_dict()

    def _parse_bang_command(self, msg: str) -> Tuple[str, str]:
        """
        '!hello there' -> ('hello', 'there')
        """
        raw = msg.lstrip("!").strip()
        if not raw:
            return "", ""
        parts = raw.split(maxsplit=1)
        name = parts[0].strip().lower()
        args = parts[1].strip() if len(parts) > 1 else ""
        return name, args

    def _check_cooldowns(
        self,
        cmd: str,
        user: str,
        now: float,
        global_cd: float,
        user_cd: float,
    ) -> Tuple[bool, float]:
        # Global per-command cooldown
        last_g = self._last_used_global.get(cmd, 0.0)
        if global_cd > 0 and (now - last_g) < global_cd:
            return False, max(0.0, global_cd - (now - last_g))

        # Per-user cooldown for this command
        key = (cmd, user)
        last_u = self._last_used_user.get(key, 0.0)
        if user_cd > 0 and (now - last_u) < user_cd:
            return False, max(0.0, user_cd - (now - last_u))

        return True, 0.0

    def _mark_used(self, cmd: str, user: str, now: float) -> None:
        self._last_used_global[cmd] = now
        self._last_used_user[(cmd, user)] = now

    def _render_response(self, template: str, *, user: str, args: str) -> str:
        """
        Safe mini-templating:
          {{user}} -> username
          {{args}} -> rest of command
        """
        out = template.replace("{{user}}", str(user))
        out = out.replace("{{args}}", str(args))
        return out

    # ---------------------------------------------------------
    # Built-in commands
    # ---------------------------------------------------------

    def _cmd_ping(self, cmd: str) -> CommandResult:
        logger.debug("Handling ping command")
        return CommandResult(status="ok", message="pong", data={"command": cmd})

    def _cmd_help(self, cmd: str) -> CommandResult:
        logger.debug("Handling help command")
        builtins = sorted(self._built_in_commands.keys())
        customs = sorted(self._custom_commands.keys())
        msg = "Built-in: " + ", ".join(builtins)
        if customs:
            msg += " | Custom: " + ", ".join(customs[:20])
            if len(customs) > 20:
                msg += " ..."
        return CommandResult(status="ok", message=msg, data={"built_in": builtins, "custom": customs})
