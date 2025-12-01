"""Understand node for processing user input and structuring tool output.

This module provides the UnderstandNode class that handles two key scenarios:
1. Processing user requests and routing to appropriate tools
2. Structuring tool outputs into human-readable responses
"""

import logging
from typing import Any

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    trim_messages,
)
from langchain_core.messages.utils import count_tokens_approximately
from pydantic import BaseModel, Field

from agent.nodes.base_node import AgentNode
from core.device_inventory import DeviceInventory
from core.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


UNDERSTAND_PROMPT = """
You are a network automation assistant.

Device inventory:
{device_inventory}

Role: Understand user requests and translate them into network operations or provide normal chat responses.

Tools:
- `show_command`: read-only (show/get/display)
- `config_command`: configuration changes (config/set/delete)
- `respond`: Final response to the user. Call this ONLY when all tasks are done.

Rules:
- Call tools only for explicit network operations; do not call for greetings or general chat.
- Match syntax to each platform. If a command fails, include the device error. Confirm successful config changes.
- Multi-device: detect target devices, produce device-specific commands per platform (IOS, EOS, JunOS, etc.).
"""


STRUCTURED_OUTPUT_PROMPT = """
You are a network automation assistant.

Your task is to analyze the provided network command output and structure it.
Do NOT call any more tools.
Analyze the output from the executed tool and return a structured JSON response.

You MUST return a JSON object with exactly these keys:
- "summary": A human-readable executive summary. Highlight operational status, health, and anomalies. Use Markdown for readability.
- "structured_data": The parsed data as a list or dictionary.
- "errors": A list of error strings (or null if none).

Example:
{
  "summary": "Interface Eth1 is up.",
  "structured_data": {"interfaces": [{"name": "Eth1", "status": "up"}]},
  "errors": []
}
"""


SUMMARY_PROMPT = """
Distill the following conversation history into a concise summary.
Include key details like device names, specific issues mentioned, and actions taken.
Do not lose important context needed for future turns.
"""


class NetworkResponse(BaseModel):
    """Structured response for network operations."""

    summary: str = Field(
        description="A human-readable summary highlighting operational status and anomalies."
    )
    structured_data: dict | list = Field(
        description="The parsed data from the device output in JSON format (list or dict)."
    )
    errors: list[str] | None = Field(
        description="List of any errors encountered during execution."
    )


class UnderstandNode(AgentNode):
    """Process user messages and structure tool outputs.

    This node has two main responsibilities:
    1. User Input: Routes to appropriate tools based on user requests
    2. Tool Output: Structures responses for human-readable display
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        device_inventory: DeviceInventory,
        tools: list,
        max_history_tokens: int = 3500,
    ):
        """Initialize the understand node.

        Args:
            llm_provider: LLMProvider instance
            device_inventory: DeviceInventory for device information
            tools: List of available tools
            max_history_tokens: Maximum tokens for conversation history
        """
        super().__init__(llm_provider)
        self._device_inventory = device_inventory
        self._tools = tools
        self._max_history_tokens = max_history_tokens

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Process user input or structure tool outputs.

        Args:
            state: Current workflow state

        Returns:
            Updated state with LLM response
        """
        messages = state.get("messages", [])

        # Trim messages for context window management
        trimmed_msgs = self._trim_messages(messages)

        try:
            # Check if processing tool output or user input
            last_msg = messages[-1] if messages else None

            if isinstance(last_msg, ToolMessage):
                # Structure tool output
                return self._structure_tool_output(trimmed_msgs)
            else:
                # Process user input and route to tools
                return self._process_user_input(trimmed_msgs)

        except Exception as e:
            logger.error(f"LLM Error: {e}")
            return self._handle_llm_error(e)

    def _trim_messages(self, messages: list) -> list:
        """Trim messages to fit within context window.

        Args:
            messages: List of messages

        Returns:
            Trimmed list of messages
        """
        try:
            trimmed_msgs = trim_messages(
                messages,
                max_tokens=self._max_history_tokens,
                strategy="last",
                token_counter=count_tokens_approximately,
                start_on="human",
                include_system=False,
                allow_partial=False,
            )

            # Log if trimming occurred
            if len(messages) > len(trimmed_msgs):
                original_tokens = count_tokens_approximately(messages)
                trimmed_tokens = count_tokens_approximately(trimmed_msgs)

                logger.info(
                    f"Context trimmed: {len(messages)} messages (~{original_tokens} tokens) "
                    f"→ {len(trimmed_msgs)} messages (~{trimmed_tokens} tokens)"
                )

                # Summarize dropped messages
                dropped_count = len(messages) - len(trimmed_msgs)
                if dropped_count > 0:
                    dropped_msgs = messages[:dropped_count]
                    summary = self._summarize_messages(dropped_msgs)

                    summary_msg = SystemMessage(
                        content=f"Previous Conversation Summary:\n{summary}"
                    )
                    trimmed_msgs = [summary_msg] + trimmed_msgs
                    logger.info("Added conversation summary for dropped messages.")

            return trimmed_msgs

        except Exception as trim_error:
            logger.warning(
                f"Message trimming failed ({type(trim_error).__name__}): {trim_error}. "
                "Using fallback strategy."
            )
            # Fallback: keep last 10 messages
            return messages[-10:] if len(messages) > 10 else messages

    def _summarize_messages(self, messages: list) -> str:
        """Summarize messages using LLM.

        Args:
            messages: List of messages to summarize

        Returns:
            Summary string
        """
        llm = self._get_llm()
        prompt = f"{SUMMARY_PROMPT}\n\nMessages:\n"
        for msg in messages:
            role = "User" if isinstance(msg, HumanMessage) else "Assistant"
            prompt += f"{role}: {msg.content}\n"

        response = llm.invoke(prompt)
        return response.content

    def _structure_tool_output(self, messages: list) -> dict[str, Any]:
        """Structure tool output into NetworkResponse format.

        Args:
            messages: Trimmed message list with tool output

        Returns:
            State dict with structured response
        """
        import json

        structured_system_msg = SystemMessage(content=STRUCTURED_OUTPUT_PROMPT)

        try:
            # Use plain LLM and parse JSON manually to avoid Groq API issues
            llm = self._get_llm()
            response = llm.invoke([structured_system_msg] + messages)

            # Parse the JSON response
            response_text = response.content

            # Try to extract JSON from the response
            try:
                # First try: parse whole response as JSON
                parsed = json.loads(response_text)
            except json.JSONDecodeError:
                # Second try: find JSON in markdown code blocks
                import re

                json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(1))
                else:
                    # Third try: find JSON object in text
                    json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group(0))
                    else:
                        raise ValueError("No JSON found in response")

            # Validate against NetworkResponse schema
            network_response = NetworkResponse(**parsed)

            # Convert to JSON string for AIMessage
            return {"messages": [AIMessage(content=network_response.model_dump_json())]}

        except Exception as struct_error:
            logger.error(f"Structured output error: {struct_error}")
            # Fallback: return raw tool message content
            last_msg = messages[-1] if messages else None
            content = last_msg.content if last_msg else "No tool output"
            return {
                "messages": [
                    AIMessage(
                        content=f"Tool output received but could not be structured: {content}"
                    )
                ]
            }

    def _process_user_input(self, messages: list) -> dict[str, Any]:
        """Process user input and route to appropriate tools.

        Args:
            messages: Trimmed message list

        Returns:
            State dict with LLM response including tool calls
        """
        # Get device inventory for prompt
        inventory_str = self._device_inventory.get_device_info()
        system_msg = SystemMessage(
            content=UNDERSTAND_PROMPT.format(device_inventory=inventory_str)
        )

        # Get LLM with tools and invoke
        llm_with_tools = self._get_llm_with_tools(self._tools)
        response = llm_with_tools.invoke([system_msg] + messages)

        return {"messages": [response]}

    def _handle_llm_error(self, error: Exception) -> dict[str, Any]:
        """Handle LLM errors with user-friendly messages.

        Args:
            error: The exception that occurred

        Returns:
            State dict with error message
        """
        err_str = str(error)

        if "429" in err_str:
            msg = "⚠️ Rate limit reached (Groq). Please wait a moment."
        elif "401" in err_str:
            msg = "⚠️ Authentication failed. Check GROQ_API_KEY."
        else:
            msg = "⚠️ An internal error occurred processing your request."

        return {"messages": [AIMessage(content=msg)]}
