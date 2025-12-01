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

        Uses function_calling method which is compatible with Groq's API.

        Args:
            schema: Pydantic model for structured output

        Returns:
            LLM configured for structured output
        """
        # Use function_calling method instead of json_mode for Groq compatibility
        # This avoids the "tool 'json' not in request.tools" error
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
            temperature=self._config.llm_temperature,
            groq_api_key=self._config.groq_api_key,
        )

    def reset(self) -> None:
        """Reset cached LLM instances.

        This can be useful for testing or when configuration changes.
        """
        self._llm = None
        self._llm_with_tools = None
