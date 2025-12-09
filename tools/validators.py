"""Centralized validation and error handling for tools."""

from typing import List

from langchain_core.exceptions import OutputParserException


class ToolValidator:
    """Centralized validation and error handling for tools.

    Uses LangChain's OutputParserException to allow the LLM to see
    validation failures when `send_to_llm=True` is set.
    """

    @staticmethod
    def validate_devices(devices: List[str]) -> None:
        """Ensure device list is not empty."""
        if not devices:
            raise OutputParserException(
                "No devices specified. Please select from the inventory using the list_devices tool."
            )

    @staticmethod
    def validate_command(command: str) -> None:
        """Ensure command is not empty."""
        if not command or not command.strip():
            raise OutputParserException("Command cannot be empty.")

    @staticmethod
    def validate_configs(configs: List[str]) -> List[str]:
        """Validate and clean configuration commands."""
        if not configs:
            raise OutputParserException("No configuration commands provided.")

        # Clean: remove empty lines, trim whitespace
        clean: List[str] = []
        for config in configs:
            for line in config.split("\n"):
                line = line.strip()
                if line:
                    clean.append(line)

        if not clean:
            raise OutputParserException("No valid configuration commands after cleanup.")

        return clean
