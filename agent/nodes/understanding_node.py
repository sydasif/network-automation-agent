"""Understanding node for processing user input and selecting tools.

This module provides the UnderstandingNode class that handles
user intent understanding and tool selection using LLM reasoning.
"""

import logging
from typing import Any

from langchain_core.messages import SystemMessage

from agent.nodes.base_node import AgentNode
from agent.prompts import NetworkAgentPrompts
from core.device_inventory import DeviceInventory
from core.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class UnderstandingNode(AgentNode):
    """Understands user intent and selects tools.

    This node processes user input, understands intent, and selects
    appropriate tools with LLM reasoning.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        device_inventory: DeviceInventory,
        tools: list,
    ):
        """Initialize the understanding node.

        Args:
            llm_provider: LLMProvider instance
            device_inventory: DeviceInventory for device information
            tools: List of available tools
        """
        super().__init__(llm_provider)
        self._device_inventory = device_inventory
        self._tools = tools

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Understand user intent and select tools.

        Args:
            state: Current workflow state

        Returns:
            Updated state with LLM response including tool calls
        """
        messages = state.get("messages", [])

        # Build system prompt with device inventory and tools
        system_msg = self._build_system_prompt()

        # Get LLM with tools and invoke
        llm_with_tools = self._get_llm_with_tools(self._tools)
        response = llm_with_tools.invoke([system_msg] + messages)

        return {"messages": [response]}

    def _build_system_prompt(self) -> SystemMessage:
        """Build system prompt with device inventory and tools info.

        Returns:
            SystemMessage with formatted prompt
        """
        # Get device inventory for prompt
        inventory_str = self._device_inventory.get_device_info()
        tools_desc = self._format_tools_description(self._tools)

        return SystemMessage(
            content=NetworkAgentPrompts.understand_system(inventory_str, tools_desc)
        )

    def _format_tools_description(self, tools: list) -> str:
        """Format tool descriptions for the prompt.

        Args:
            tools: List of tool instances

        Returns:
            Formatted string of tool descriptions
        """
        descriptions = []
        for tool in tools:
            # Handle both LangChain tools and our custom tools
            name = getattr(tool, "name", str(tool))
            description = getattr(tool, "description", "")
            descriptions.append(f"- `{name}`: {description}")

        return "\n\n".join(descriptions)
