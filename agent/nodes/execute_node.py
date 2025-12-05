"""Execute node for running tools."""

from typing import Any

from langgraph.prebuilt import ToolNode

from agent.nodes.base_node import AgentNode
from core.llm_provider import LLMProvider


class ExecuteNode(AgentNode):
    """Execute node for running network automation tools."""

    def __init__(self, llm_provider: LLMProvider, tools: list):
        super().__init__(llm_provider)
        # Enable built-in error handling
        self._tool_node = ToolNode(tools, handle_tool_errors=True)

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute the tools from the last message."""
        # Delegate to LangGraph's ToolNode
        return self._tool_node.invoke(state)
