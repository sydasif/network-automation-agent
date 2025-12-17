"""LLM provider for the Network AI Agent with monitoring integration.

This module provides the LLMProvider class that manages
LLM instance creation and lifecycle.
"""

import logging

from langchain_core.language_models import BaseChatModel
from langchain_groq import ChatGroq

from core.config import NetworkAgentConfig
from core.message_manager import MessageManager

# Import monitoring components
from monitoring.tracing import get_callback_handler

logger = logging.getLogger(__name__)


class LLMProvider:
    """Provides LLM instances with proper configuration.

    This class manages the creation and caching of LLM instances,
    supporting both base LLM and LLM with tools/structured output.
    """

    def __init__(self, config: NetworkAgentConfig, enable_monitoring: bool = True):
        """Initialize the LLM provider.

        Args:
            config: NetworkAgentConfig instance
            enable_monitoring: Whether to enable monitoring for LLM calls
        """
        self._config = config
        self._primary_llm: BaseChatModel | None = None
        self._message_manager = MessageManager(max_tokens=self._config.max_history_tokens)
        self._enable_monitoring = enable_monitoring
        self._callback_handler = get_callback_handler() if enable_monitoring else None

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
        # Bind callbacks for monitoring if enabled
        if self._enable_monitoring and self._callback_handler:
            return base_llm.bind(callbacks=[self._callback_handler])
        return base_llm.bind_tools(tools)

    def _create_llm(self, model_name: str, temperature: float) -> BaseChatModel:
        """Create and configure a new LLM instance.

        Args:
            model_name: Name of the model
            temperature: Temperature setting

        Returns:
            Configured ChatGroq instance
        """
        logger.debug(f"Initializing LLM with model: {model_name}, temperature: {temperature}")

        # Create LLM with callbacks if monitoring is enabled
        if self._enable_monitoring and self._callback_handler:
            return ChatGroq(
                model=model_name,
                # Use the exact temperature from config for deterministic behavior
                temperature=temperature,
                groq_api_key=self._config.groq_api_key,
                max_retries=3,
                callbacks=[self._callback_handler]  # Add monitoring callbacks
            )
        else:
            return ChatGroq(
                model=model_name,
                # Use the exact temperature from config for deterministic behavior
                temperature=temperature,
                groq_api_key=self._config.groq_api_key,
                max_retries=3,
            )
