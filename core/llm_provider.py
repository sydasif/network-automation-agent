"""LLM provider for the Network AI Agent.

This module provides the LLMProvider class that manages
LLM instance creation and lifecycle.
"""

import logging

from langchain_core.language_models import BaseChatModel
from langchain_groq import ChatGroq
from pydantic import BaseModel

from core.config import NetworkAgentConfig

logger = logging.getLogger(__name__)


class LLMProvider:
    """Provides LLM instances with proper configuration.

    This class manages the creation and caching of LLM instances,
    supporting both base LLM and LLM with tools/structured output.
    """

    def __init__(self, config: NetworkAgentConfig):
        """Initialize the LLM provider.

        Args:
            config: NetworkAgentConfig instance
        """
        self._config = config
        self._llm: BaseChatModel | None = None
        self._llm_with_tools: BaseChatModel | None = None

    def get_llm(self) -> BaseChatModel:
        """Get base LLM instance (lazy-loaded singleton).

        Returns:
            Configured LLM instance

        Raises:
            RuntimeError: If GROQ_API_KEY is not configured
        """
        if self._llm is None:
            self._llm = self._create_llm()
        return self._llm

    def get_llm_with_tools(self, tools: list) -> BaseChatModel:
        """Get LLM instance with tools bound.

        Args:
            tools: List of tools to bind to LLM

        Returns:
            LLM instance with tools bound
        """
        # Note: We recreate this each time since tools may change
        # In the future, we could cache based on tool list
        base_llm = self.get_llm()
        return base_llm.bind_tools(tools)

    def create_structured_llm(self, schema: type[BaseModel]):
        """Create LLM with structured output.

        **WARNING - Groq API Incompatibility with some models**:
        The `with_structured_output()` method may cause Groq API errors with certain models
        (e.g., openai/gpt-oss-*):
        - Error: "Tool choice is required, but model did not call a tool"
        - Error: "attempted to call tool 'json' which was not in request.tools"

        **Recommendation**: Use manual JSON parsing for broader model compatibility.
        See UnderstandNode._structure_tool_output() and PlannerNode.execute()
        for the recommended pattern.

        Args:
            schema: Pydantic model for structured output

        Returns:
            LLM configured for structured output
        """
        return self.get_llm().with_structured_output(schema)

    def _create_llm(self) -> BaseChatModel:
        """Create and configure a new LLM instance.

        Returns:
            Configured ChatGroq instance

        Raises:
            RuntimeError: If GROQ_API_KEY is not set
        """
        logger.debug(
            f"Initializing LLM with model: {self._config.llm_model_name}, "
            f"temperature: {self._config.llm_temperature}"
        )

        return ChatGroq(
            model=self._config.llm_model_name,
            # Increased temperature to 0.2 to encourage parallel tool calling
            temperature=max(self._config.llm_temperature, 0.2),
            groq_api_key=self._config.groq_api_key,
        )

    def reset(self) -> None:
        """Reset cached LLM instances.

        This can be useful for testing or when configuration changes.
        """
        self._llm = None
        self._llm_with_tools = None
