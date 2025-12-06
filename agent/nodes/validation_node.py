"""Validation node for validating tool calls before execution.

This module provides the ValidationNode class that handles
validation of tool calls, device names, and command validity.
"""

import logging
from typing import Any

from langchain_core.messages import AIMessage

from agent.constants import TOOL_CONFIG_COMMAND, TOOL_SHOW_COMMAND
from agent.nodes.base_node import AgentNode
from core.device_inventory import DeviceInventory
from core.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class ValidationNode(AgentNode):
    """Validates tool calls before execution.

    This node validates tool calls for device names, command validity,
    and other constraints before allowing execution to proceed.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        device_inventory: DeviceInventory,
    ):
        """Initialize the validation node.

        Args:
            llm_provider: LLMProvider instance
            device_inventory: DeviceInventory for device validation
        """
        super().__init__(llm_provider)
        self._device_inventory = device_inventory

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Validate tool calls before execution.

        Args:
            state: Current workflow state

        Returns:
            Updated state with validation result
        """

        last_msg = self._get_latest_tool_message(state)

        if not last_msg:
            return state

        # Validate tool calls
        validation_result = self._validate_tool_calls(last_msg)

        if validation_result.is_valid:
            return state
        else:
            # Return validation error as a new message
            error_msg = AIMessage(content=f"❌ Validation Error: {validation_result.error}")
            return {"messages": [error_msg]}

    def _validate_tool_calls(self, response: AIMessage):
        """Validate tool calls for device names and command validity.

        Args:
            response: AIMessage from LLM with potential tool calls

        Returns:
            ValidationResult object with validation status and error message
        """
        # If no tool calls, return as-is
        if not hasattr(response, "tool_calls") or not response.tool_calls:
            return ValidationResult(True, "")

        # Check each tool call for validation
        for tool_call in response.tool_calls:
            tool_name = tool_call.get("name", "")
            tool_args = tool_call.get("args", {})

            # Validate device names for network operation tools
            if tool_name in [TOOL_SHOW_COMMAND, TOOL_CONFIG_COMMAND]:
                devices = tool_args.get("devices", [])

                if not devices:
                    return ValidationResult(
                        False,
                        "No devices specified for network operation. "
                        "Please specify target devices from the inventory.",
                    )

                # Validate devices exist in inventory
                valid, invalid = self._device_inventory.validate_devices(devices)

                if invalid:
                    available = self._device_inventory.get_all_device_names()
                    return ValidationResult(
                        False,
                        f"Unknown devices: {', '.join(sorted(invalid))}.\n"
                        f"Available devices: {', '.join(available)}\n\n"
                        "Please use only devices from the inventory above.",
                    )

                # Validate command/configs are non-empty
                if tool_name == TOOL_SHOW_COMMAND:
                    command = tool_args.get("command", "").strip()
                    if not command:
                        return ValidationResult(
                            False, "Command cannot be empty. Please provide a valid show command."
                        )

                elif tool_name == TOOL_CONFIG_COMMAND:
                    configs = tool_args.get("configs", [])
                    if not configs or all(not c.strip() for c in configs):
                        return ValidationResult(
                            False,
                            "Configuration commands cannot be empty. "
                            "Please provide valid configuration commands.",
                        )

        # All validations passed
        return ValidationResult(True, "")


class ValidationResult:
    """Simple class to hold validation results."""

    def __init__(self, is_valid: bool, error: str = ""):
        self.is_valid = is_valid
        self.error = error
