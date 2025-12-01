"""Base class for agent workflow nodes.

This module provides the AgentNode abstract base class that defines
the interface for all workflow nodes.
"""

from abc import ABC, abstractmethod
from typing import Any

from core.llm_provider import LLMProvider


class AgentNode(ABC):
    """Base class for agent workflow nodes.

    All workflow nodes should inherit from this class and implement
    the execute method. Nodes are responsible for one specific aspect
    of the agent workflow.
    """

    def __init__(self, llm_provider: LLMProvider):
        """Initialize the agent node.

        Args:
            llm_provider: LLMProvider instance for accessing LLM
        """
        self._llm_provider = llm_provider

    @abstractmethod
    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute the node logic.

        Args:
            state: Current workflow state containing messages and other data

        Returns:
            Updated workflow state
        """
        pass

    def _get_llm(self):
        """Get the base LLM instance.

        Returns:
            Configured LLM instance
        """
        return self._llm_provider.get_llm()

    def _get_llm_with_tools(self, tools: list):
        """Get LLM with tools bound.

        Args:
            tools: List of tools to bind

        Returns:
            LLM with tools bound
        """
        return self._llm_provider.get_llm_with_tools(tools)

    def _get_structured_llm(self, schema):
        """Get LLM with structured output.

        Args:
            schema: Pydantic model for structured output

        Returns:
            LLM configured for structured output
        """
        return self._llm_provider.create_structured_llm(schema)
