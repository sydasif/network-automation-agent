"""Command processor for CLI commands.

This module provides the CommandProcessor class for parsing
and validating CLI commands.
"""

import logging
import re

from core.device_inventory import DeviceInventory

logger = logging.getLogger(__name__)


class CommandProcessor:
    """Process and validate CLI commands.

    This class handles command parsing and validation logic
    to ensure commands are well-formed before execution.
    """

    def __init__(self, device_inventory: DeviceInventory):
        """Initialize the command processor.

        Args:
            device_inventory: DeviceInventory for device validation
        """
        self._device_inventory = device_inventory

    def parse_command(self, command: str, default_device: str | None = None) -> dict:
        """Parse command string into structured format.

        Args:
            command: Raw command string
            default_device: Optional default device

        Returns:
            Dict with parsed command information:
            {
                'original': str,           # Original command
                'command': str,            # Processed command
                'devices': list[str],      # Target devices (may be empty)
                'has_device_context': bool # Whether devices were specified
            }
        """
        parsed = {
            "original": command,
            "command": command,
            "devices": [],
            "has_device_context": False,
        }

        # Extract device references (e.g., "on device sw1" or "on sw1, sw2")
        device_pattern = r"\bon\s+(?:device\s+)?([a-zA-Z0-9_,\s-]+)$"
        match = re.search(device_pattern, command, re.IGNORECASE)

        if match:
            device_str = match.group(1)
            # Parse comma-separated devices
            devices = [d.strip() for d in device_str.split(",") if d.strip()]
            parsed["devices"] = devices
            parsed["has_device_context"] = True
            # Remove device context from command
            parsed["command"] = command[: match.start()].strip()

        # Add default device if provided and no devices found
        if default_device and not parsed["devices"]:
            parsed["devices"] = [default_device]
            parsed["has_device_context"] = True

        return parsed

    def validate_command(self, parsed_command: dict) -> tuple[bool, str]:
        """Validate parsed command.

        Args:
            parsed_command: Parsed command dict from parse_command

        Returns:
            Tuple of (is_valid, error_message)
            error_message is empty string if valid
        """
        # Check if command is empty
        if not parsed_command["command"].strip():
            return False, "Command cannot be empty"

        # Validate devices if specified
        if parsed_command["devices"]:
            valid, invalid = self._device_inventory.validate_devices(parsed_command["devices"])

            if invalid:
                available = self._device_inventory.get_all_device_names()
                return (
                    False,
                    f"Unknown devices: {', '.join(invalid)}. Available: {', '.join(available)}",
                )

        return True, ""

    def suggest_devices(self, partial_name: str) -> list[str]:
        """Suggest device names based on partial input.

        Args:
            partial_name: Partial device name

        Returns:
            List of matching device names
        """
        all_devices = self._device_inventory.get_all_device_names()
        partial_lower = partial_name.lower()

        return [device for device in all_devices if partial_lower in device.lower()]
