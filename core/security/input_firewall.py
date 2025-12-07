# core/security/input_firewall.py

from __future__ import annotations

from typing import List

from core.logger import get_logger


# Very simple list of dangerous patterns to block / redact.
DANGEROUS_PATTERNS: List[str] = [
    "rm -rf",
    "format C:",
    "shutdown",
    "del /f /q",
    "mkfs",
    "poweroff",
]


class InputFirewall:
    """
    Basic input firewall.
    - Logs any dangerous patterns it sees
    - Returns a sanitized version of the text
    """

    def __init__(self) -> None:
        self.logger = get_logger("security")

    def sanitize(self, text: str) -> str:
        cleaned = text
        lowered = text.lower()

        for pattern in DANGEROUS_PATTERNS:
            if pattern.lower() in lowered:
                self.logger.warning("Blocked dangerous pattern: %r", pattern)
                # Redact the exact pattern in the original text
                cleaned = cleaned.replace(pattern, "[BLOCKED]")

        return cleaned


_firewall_singleton: InputFirewall | None = None


def get_firewall() -> InputFirewall:
    global _firewall_singleton
    if _firewall_singleton is None:
        _firewall_singleton = InputFirewall()
    return _firewall_singleton


def sanitize_input(text: str) -> str:
    """
    Convenience function so other code can just call:
    from core.security.input_firewall import sanitize_input
    """
    return get_firewall().sanitize(text)


if __name__ == "__main__":
    fw = get_firewall()
    print(fw.sanitize("run this: rm -rf C: && shutdown"))
    print(sanitize_input("format C: please"))
