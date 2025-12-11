"""Centralized validation and error handling for tools."""

import re
from typing import List

from langchain_core.exceptions import OutputParserException


class ToolValidator:
    """Centralized validation and error handling for tools.

    Uses LangChain's OutputParserException to allow the LLM to see
    validation failures when `send_to_llm=True` is set.
    """

    # Regex patterns for network commands
    DEVICE_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9._-]+$')
    SHOW_COMMAND_PATTERN = re.compile(r'^(show|display|sh)\s+[\w\s\-_\/\.]+$', re.IGNORECASE)
    CONFIG_COMMAND_PATTERN = re.compile(r'^[\w\s\-_\/\.]+$', re.IGNORECASE)

    @staticmethod
    def validate_devices(devices: List[str]) -> None:
        """Ensure device list is not empty and contains valid device names."""
        if not devices:
            raise OutputParserException(
                "No devices specified. Please select from the inventory using the list_devices tool."
            )

        for device in devices:
            if not device or not device.strip():
                raise OutputParserException(f"Invalid device name: '{device}'. Device names cannot be empty.")

            if not ToolValidator.DEVICE_NAME_PATTERN.match(device.strip()):
                raise OutputParserException(
                    f"Invalid device name: '{device}'. Device names can only contain letters, numbers, dots, underscores, and hyphens."
                )

    @staticmethod
    def validate_command(command: str) -> str:
        """Ensure command is not empty and follows proper format."""
        if not command or not command.strip():
            raise OutputParserException("Command cannot be empty.")

        command = command.strip()

        # Check if command looks like a show command
        if not ToolValidator.SHOW_COMMAND_PATTERN.match(command):
            # Provide more specific feedback for common issues
            if 'configure' in command.lower() or 'config' in command.lower():
                raise OutputParserException(
                    f"Command '{command}' appears to be a configuration command. "
                    "Use the config_command tool for configuration changes instead of the show_command tool."
                )
            elif len(command.split()) < 2:
                raise OutputParserException(
                    f"Command '{command}' is too short. Show commands typically follow the format: 'show <object>' (e.g., 'show version', 'show ip interface brief')."
                )

        return command

    @staticmethod
    def validate_configs(configs: List[str]) -> List[str]:
        """Validate and clean configuration commands with enhanced checks."""
        if not configs:
            raise OutputParserException("No configuration commands provided.")

        # Clean: remove empty lines, trim whitespace
        clean: List[str] = []
        for config in configs:
            for line in config.split("\n"):
                line = line.strip()
                if line:
                    # Basic validation for configuration commands
                    if not ToolValidator.CONFIG_COMMAND_PATTERN.match(line):
                        raise OutputParserException(
                            f"Invalid configuration command format: '{line}'. "
                            "Configuration commands should contain valid network syntax."
                        )
                    clean.append(line)

        if not clean:
            raise OutputParserException("No valid configuration commands after cleanup.")

        return clean

    @staticmethod
    def validate_show_command_semantics(command: str) -> None:
        """Validate that the show command is semantically appropriate."""
        if not command or not command.strip():
            return

        command_lower = command.lower().strip()

        # Check for potentially dangerous or inappropriate commands
        dangerous_patterns = [
            r'\b(delete|format|erase|clear counters|reload|reboot)\b',
            r'\bwrite\s+erase\b',
            r'\bcopy\s+.*\s+null\b'
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, command_lower):
                raise OutputParserException(
                    f"The command '{command}' appears to be a destructive operation that should be performed via the config_command tool, not the show_command tool."
                )

    @staticmethod
    def validate_config_command_semantics(configs: List[str]) -> None:
        """Validate that config commands are semantically appropriate."""
        if not configs:
            return

        for config in configs:
            config_lower = config.lower()

            # Check for show commands in config context
            show_indicators = ['show', 'display', 'sh', 'dir', 'ls']
            for indicator in show_indicators:
                if config_lower.startswith(indicator):
                    raise OutputParserException(
                        f"Configuration command '{config}' appears to be a show command. "
                        "Use the show_command tool for read-only operations."
                    )
