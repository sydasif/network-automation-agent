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
from agent.prompts import NetworkAgentPrompts
from core.device_inventory import DeviceInventory
from core.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


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
        prompt = f"{NetworkAgentPrompts.summary_system}\n\nMessages:\n"
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

        # Get only the last ToolMessage (the actual output we need to structure)
        last_tool_msg = None
        for msg in reversed(messages):
            if isinstance(msg, ToolMessage):
                last_tool_msg = msg
                break

        if not last_tool_msg:
            return {"messages": [AIMessage(content="No tool output to structure")]}

        # Create a focused prompt that only asks to structure THIS specific output
        structured_system_msg = SystemMessage(
            content=NetworkAgentPrompts.structured_output_system(last_tool_msg.content)
        )

        try:
            # Use plain LLM (NOT with tools) to avoid unwanted tool calls
            llm = self._get_llm()

            # Only pass the system message - do NOT include message history
            # This prevents the LLM from trying to continue the conversation
            response = llm.invoke([structured_system_msg])

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
            content = last_tool_msg.content if last_tool_msg else "No tool output"
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
        tools_desc = self._format_tools_description(self._tools)
        system_msg = SystemMessage(
            content=NetworkAgentPrompts.understand_system(inventory_str, tools_desc)
        )

        # Get LLM with tools and invoke
        llm_with_tools = self._get_llm_with_tools(self._tools)
        response = llm_with_tools.invoke([system_msg] + messages)

        # Validate tool calls before returning
        validated_response = self._validate_tool_calls(response)

        return {"messages": [validated_response]}

    def _validate_tool_calls(self, response: AIMessage) -> AIMessage:
        """Validate tool calls for device names and command validity.

        Args:
            response: AIMessage from LLM with potential tool calls

        Returns:
            Original response if valid, or new AIMessage with error if invalid
        """
        # If no tool calls, return as-is
        if not hasattr(response, "tool_calls") or not response.tool_calls:
            return response

        # Check each tool call for validation
        for tool_call in response.tool_calls:
            tool_name = tool_call.get("name", "")
            tool_args = tool_call.get("args", {})

            # Validate device names for network operation tools
            if tool_name in ["show_command", "config_command"]:
                devices = tool_args.get("devices", [])

                if not devices:
                    return AIMessage(
                        content="⚠️ Error: No devices specified for network operation. "
                        "Please specify target devices from the inventory."
                    )

                # Validate devices exist in inventory
                valid, invalid = self._device_inventory.validate_devices(devices)

                if invalid:
                    available = self._device_inventory.get_all_device_names()
                    return AIMessage(
                        content=f"⚠️ Error: Unknown devices: {', '.join(sorted(invalid))}.\n"
                        f"Available devices: {', '.join(available)}\n\n"
                        "Please use only devices from the inventory above."
                    )

                # Validate command/configs are non-empty
                if tool_name == "show_command":
                    command = tool_args.get("command", "").strip()
                    if not command:
                        return AIMessage(
                            content="⚠️ Error: Command cannot be empty. "
                            "Please provide a valid show command."
                        )

                elif tool_name == "config_command":
                    configs = tool_args.get("configs", [])
                    if not configs or all(not c.strip() for c in configs):
                        return AIMessage(
                            content="⚠️ Error: Configuration commands cannot be empty. "
                            "Please provide valid configuration commands."
                        )

        # All validations passed
        return response

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
