"""Configuration settings for the Network AI Agent.

This module contains the NetworkAgentConfig class that manages all
configuration variables used throughout the application.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


class NetworkAgentConfig:
    """Centralized configuration for the Network AI Agent.

    This class loads and validates all configuration from environment variables.
    It provides a single source of truth for application settings.
    """

    def __init__(self, env_file: str = ".env"):
        """Load configuration from environment.

        Args:
            env_file: Path to .env file (default: ".env")
        """
        # Load environment variables from .env file
        load_dotenv(env_file)

        # Store base directory
        self._base_dir = Path(__file__).resolve().parent.parent

        # Load configuration values
        self._groq_api_key = os.getenv("GROQ_API_KEY")
        self._llm_model_name = os.getenv("LLM_MODEL_NAME", "openai/gpt-oss-20b")
        self._llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0.0"))
        self._max_history_tokens = int(os.getenv("MAX_HISTORY_TOKENS", "2000"))

        # Nornir configuration
        self._num_workers = int(os.getenv("NUM_WORKERS", "20"))
        self._netmiko_timeout = int(os.getenv("NETMIKO_TIMEOUT", "30"))
        self._netmiko_conn_timeout = int(os.getenv("NETMIKO_CONN_TIMEOUT", "10"))
        self._netmiko_session_timeout = int(os.getenv("NETMIKO_SESSION_TIMEOUT", "60"))

        # Logging configuration
        self._log_skip_modules = [
            "httpcore",
            "httpx",
            "markdown_it",
            "groq._base_client",
        ]

    @property
    def base_dir(self) -> Path:
        """Get the base directory of the project."""
        return self._base_dir

    @property
    def groq_api_key(self) -> str:
        """Get GROQ API key.

        Returns:
            GROQ API key

        Raises:
            RuntimeError: If GROQ_API_KEY is not set
        """
        if not self._groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY environment variable is required. "
                "Please set it in your .env file or environment."
            )
        return self._groq_api_key

    @property
    def llm_model_name(self) -> str:
        """Get LLM model name."""
        return self._llm_model_name

    @property
    def llm_temperature(self) -> float:
        """Get LLM temperature setting."""
        return self._llm_temperature

    @property
    def max_history_tokens(self) -> int:
        """Get maximum tokens for conversation history."""
        return self._max_history_tokens

    @property
    def num_workers(self) -> int:
        """Get number of parallel workers for Nornir."""
        return self._num_workers

    @property
    def netmiko_timeout(self) -> int:
        """Get default timeout for Netmiko commands in seconds."""
        return self._netmiko_timeout

    @property
    def netmiko_conn_timeout(self) -> int:
        """Get connection timeout for Netmiko in seconds."""
        return self._netmiko_conn_timeout

    @property
    def netmiko_session_timeout(self) -> int:
        """Get session timeout for Netmiko in seconds."""
        return self._netmiko_session_timeout

    @property
    def log_skip_modules(self) -> list[str]:
        """Get list of module names whose logs should be skipped."""
        return self._log_skip_modules

    def validate(self) -> None:
        """Validate required configuration is present.

        Raises:
            RuntimeError: If required configuration is missing
        """
        # This will raise if GROQ_API_KEY is not set
        _ = self.groq_api_key
