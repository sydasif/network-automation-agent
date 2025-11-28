"""Reusable Pydantic validators and command safety checks."""

import logging
from typing import Annotated, Any

from pydantic import BeforeValidator

logger = logging.getLogger(__name__)


def _ensure_list(v: Any) -> list[str]:
    """Coerce string input to a list of strings."""
    if isinstance(v, str):
        return [v]
    return v


FlexibleList = Annotated[list[str], BeforeValidator(_ensure_list)]


# 🆕 ADD THESE CONSTANTS
DANGEROUS_COMMANDS = {
    "reload", "reboot", "restart", "write erase", "erase", "delete",
    "format", "rmdir", "copy run start"  # Saving should be explicit via our tool
}

READ_ONLY_PREFIXES = {
    "show", "display",  # Cisco/HP
    "get",              # Juniper
    "list",             # Some vendors
}


# 🆕 ADD THIS FUNCTION
def is_safe_show_command(command: str) -> tuple[bool, str | None]:
    """Validate that a command is read-only.

    Returns:
        (is_valid, error_message)
    """
    cmd_lower = command.lower().strip()

    # Check if it starts with read-only prefix
    if not any(cmd_lower.startswith(prefix) for prefix in READ_ONLY_PREFIXES):
        return False, f"Show commands must start with: {', '.join(READ_ONLY_PREFIXES)}"

    # Check for dangerous keywords
    for dangerous in DANGEROUS_COMMANDS:
        if dangerous in cmd_lower:
            return False, f"Command contains dangerous keyword: '{dangerous}'"

    return True, None


# 🆕 ADD THIS FUNCTION
def is_safe_config_command(commands: list[str]) -> tuple[bool, str | None]:
    """Validate configuration commands for safety."""
    for cmd in commands:
        cmd_lower = cmd.lower().strip()

        # Block obviously dangerous commands
        for dangerous in DANGEROUS_COMMANDS:
            if dangerous in cmd_lower:
                return False, f"Blocked dangerous command: '{cmd}' contains '{dangerous}'"

        # Warn about suspicious patterns (but don't block)
        if "no " in cmd_lower and ("interface" in cmd_lower or "ip" in cmd_lower):
            logger.warning(f"Potentially destructive command detected: {cmd}")

    return True, None
