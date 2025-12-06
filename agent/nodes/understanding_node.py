"""Understanding node for processing user input and selecting tools."""

import logging
from typing import Any
from langchain_core.messages import AIMessage, SystemMessage

from agent.nodes.base_node import AgentNode
from agent.prompts import NetworkAgentPrompts
from core.device_inventory import DeviceInventory
from core.llm_provider import LLMProvider
from utils.memory import sanitize_messages

logger = logging.getLogger(__name__)

class UnderstandingNode(AgentNode):
    """Understands user intent and selects tools."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        device_inventory: DeviceInventory,
        tools: list,
    ):
        super().__init__(llm_provider)
        self._device_inventory = device_inventory
        self._tools = tools
        self._max_tokens = llm_provider._config.max_history_tokens

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Understand user intent and select tools."""
        messages = state.get("messages", [])

        # Check if the previous attempt failed (empty AI message)
        # This acts as a self-correction loop
        if len(messages) > 1 and isinstance(messages[-1], AIMessage):
            last_msg = messages[-1]
            if not last_msg.content and not last_msg.tool_calls:
                # Inject a hint to the LLM
                messages.append(SystemMessage(content="Error: You returned an empty response. Please clarify the request or call a tool."))

        # --- APPLY MEMORY MIDDLEWARE ---
        safe_messages = sanitize_messages(messages, max_tokens=self._max_tokens)
        # -------------------------------

        # Get device inventory
        inventory_str = self._device_inventory.get_device_info()

        # Generate prompt
        prompt = NetworkAgentPrompts.UNDERSTAND_PROMPT.invoke(
            {
                "device_inventory": inventory_str,
                "messages": safe_messages,
            }
        )

        # Get LLM with tools and invoke
        llm_with_tools = self._get_llm_with_tools(self._tools)
        response = llm_with_tools.invoke(prompt)

        # Logging
        if hasattr(response, "tool_calls") and response.tool_calls:
            logger.info(f"Generated {len(response.tool_calls)} tool calls")
        else:
            logger.info("Generated 0 tool calls")

        return {"messages": [response]}

    def _format_tools_description(self, tools: list) -> str:
        """Format tool descriptions for the prompt."""
        descriptions = []
        for tool in tools:
            name = getattr(tool, "name", str(tool))
            description = getattr(tool, "description", "")
            descriptions.append(f"- `{name}`: {description}")
        return "\n\n".join(descriptions)
