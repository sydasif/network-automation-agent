"""Format node for structuring tool outputs.

This module provides the FormatNode class that uses the format_output tool
to structure network command outputs via tool calling instead of manual JSON parsing.
"""

import logging
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage

from agent.nodes.base_node import AgentNode
from agent.prompts import NetworkAgentPrompts
from core.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class FormatNode(AgentNode):
    """Format tool outputs using tool-based structured output.

    This node binds the format_output tool to the LLM, allowing it to
    return structured data via tool calling instead of manual JSON parsing.
    This avoids Groq API issues with with_structured_output().
    """

    def __init__(self, llm_provider: LLMProvider, format_tool):
        """Initialize the format node.

        Args:
            llm_provider: LLMProvider instance
            format_tool: FormatOutputTool instance
        """
        super().__init__(llm_provider)
        self._format_tool = format_tool

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Format tool output using format_output tool.

        Args:
            state: Current workflow state

        Returns:
            Updated state with formatted response
        """
        messages = state.get("messages", [])
        if not messages:
            return state

        # Get the last ToolMessage (the output to format)
        last_tool_msg = None
        for msg in reversed(messages):
            if isinstance(msg, ToolMessage):
                last_tool_msg = msg
                break

        if not last_tool_msg:
            return {"messages": [AIMessage(content="No tool output to format")]}

        # Create system prompt for formatting using centralized prompt
        system_msg = SystemMessage(
            content=NetworkAgentPrompts.format_system(last_tool_msg.content)
        )

        try:
            # Bind format_output tool to LLM
            llm_with_tool = self._get_llm_with_tools([self._format_tool.to_langchain_tool()])

            # LLM will call format_output tool with structured arguments
            response = llm_with_tool.invoke([system_msg])

            # Check if LLM called the tool
            if hasattr(response, "tool_calls") and response.tool_calls:
                # Execute the tool call
                from langgraph.prebuilt import ToolNode

                tool_node = ToolNode([self._format_tool.to_langchain_tool()])
                tool_result = tool_node.invoke({"messages": [response]})

                # Return the tool result
                return tool_result

            # Fallback: LLM didn't call the tool
            logger.warning("LLM did not call format_output tool, returning raw response")
            return {"messages": [response]}

        except Exception as e:
            logger.error(f"Format error: {e}")
            # Fallback: return raw tool output
            return {
                "messages": [
                    AIMessage(content=f"Tool output (could not format): {last_tool_msg.content}")
                ]
            }
