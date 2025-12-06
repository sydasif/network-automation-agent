"""Format node for structuring tool outputs."""

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from agent.nodes.base_node import AgentNode
from agent.prompts import NetworkAgentPrompts
from core.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class FormatNode(AgentNode):
    """Format tool outputs using tool-based structured output."""

    def __init__(self, llm_provider: LLMProvider, format_tool):
        super().__init__(llm_provider)
        self._format_tool = format_tool

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Format tool output using format_output tool."""
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

        # Use new ChatPromptTemplate
        prompt = NetworkAgentPrompts.FORMAT_PROMPT.invoke({"tool_output": last_tool_msg.content})

        try:
            # Bind format_output tool to LLM
            llm_with_tool = self._get_llm_with_tools([self._format_tool.to_langchain_tool()])

            # Invoke LLM with the formatted prompt
            response = llm_with_tool.invoke(prompt)

            # Check if LLM called the tool
            if hasattr(response, "tool_calls") and response.tool_calls:
                from langgraph.prebuilt import ToolNode

                tool_node = ToolNode([self._format_tool.to_langchain_tool()])
                tool_result = tool_node.invoke({"messages": [response]})
                return tool_result

            # Fallback: LLM didn't call the tool
            logger.warning("LLM did not call format_output tool, returning raw response")
            return {"messages": [response]}

        except Exception as e:
            logger.error(f"Format error: {e}")

            # Graceful Fallback: Return the raw content formatted nicely
            raw_content = last_tool_msg.content
            try:
                # If it's JSON, pretty print it
                parsed = json.loads(raw_content)
                pretty_json = json.dumps(parsed, indent=2)
                return {"messages": [AIMessage(content=f"```json\n{pretty_json}\n```")]}
            except Exception:
                # If text, just wrap it
                return {"messages": [AIMessage(content=f"```text\n{raw_content}\n```")]}
