"""Execute node for running tools.

This module provides the ExecuteNode class that wraps LangGraph's
ToolNode for executing network automation tools.
"""

from typing import Any

from langgraph.prebuilt import ToolNode

from agent.nodes.base_node import AgentNode
from core.llm_provider import LLMProvider


class ExecuteNode(AgentNode):
    """Execute node for running network automation tools.

    This node wraps LangGraph's ToolNode to execute the tools
    that were called by the understand node.
    """

    def __init__(self, llm_provider: LLMProvider, tools: list):
        """Initialize the execute node.

        Args:
            llm_provider: LLMProvider instance
            tools: List of tools to make available for execution
        """
        super().__init__(llm_provider)
        self._tool_node = ToolNode(tools)

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute the tools from the last message.

        Args:
            state: Current workflow state

        Returns:
            Updated state with tool execution results
        """
        # Delegate to LangGraph's ToolNode
        return self._tool_node.invoke(state)
