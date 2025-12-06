"""LLM provider for the Network AI Agent.

This module provides the LLMProvider class that manages
LLM instance creation and lifecycle.
"""

import logging

from langchain_core.language_models import BaseChatModel
from langchain_groq import ChatGroq
from pydantic import BaseModel

from core.config import NetworkAgentConfig
from core.token_manager import TokenManager

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
        self._primary_llm: BaseChatModel | None = None
        self._secondary_llm: BaseChatModel | None = None
        self._token_manager = TokenManager()

    def get_primary_llm(self) -> BaseChatModel:
        """Get Primary LLM instance (High Reasoning).

        Returns:
            Configured LLM instance
        """
        if self._primary_llm is None:
            self._primary_llm = self._create_llm(
                model_name=self._config.llm_model_name, temperature=self._config.llm_temperature
            )
        return self._primary_llm

    def get_secondary_llm(self) -> BaseChatModel:
        """Get Secondary LLM instance (Fast/Formatting).

        Returns:
            Configured LLM instance
        """
        if self._secondary_llm is None:
            self._secondary_llm = self._create_llm(
                model_name=self._config.llm_model_secondary,
                temperature=0.0,  # Always 0 for strict formatting
            )
        return self._secondary_llm

    def get_llm(self) -> BaseChatModel:
        """Legacy alias for get_primary_llm."""
        return self.get_primary_llm()

    def get_llm_with_tools(self, tools: list) -> BaseChatModel:
        """Get Primary LLM instance with tools bound.

        Args:
            tools: List of tools to bind to LLM

        Returns:
            LLM instance with tools bound
        """
        base_llm = self.get_primary_llm()
        return base_llm.bind_tools(tools)

    def create_structured_llm(self, schema: type[BaseModel]):
        """Create Secondary LLM with structured output.

        Using Secondary LLM for formatting tasks is cheaper and faster.
        """
        return self.get_secondary_llm().with_structured_output(schema)

    def _create_llm(self, model_name: str, temperature: float) -> BaseChatModel:
        """Create and configure a new LLM instance.

        Args:
            model_name: Name of the model
            temperature: Temperature setting

        Returns:
            Configured ChatGroq instance
        """
        logger.debug(f"Initializing LLM with model: {model_name}, temperature: {temperature}")

        return ChatGroq(
            model=model_name,
            # Increased temperature to 0.2 to encourage parallel tool calling
            temperature=max(temperature, 0.2) if temperature > 0 else 0,
            groq_api_key=self._config.groq_api_key,
            max_retries=3,
        )

    def check_safe_to_send(self, messages: list) -> bool:
        """Check if message payload is safe to send.

        Args:
            messages: List of messages

        Returns:
            True if safe
        """
        return self._token_manager.check_safe_to_send(messages)

    def reset(self) -> None:
        """Reset cached LLM instances."""
        self._primary_llm = None
        self._secondary_llm = None
