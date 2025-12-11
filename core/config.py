"""Configuration settings for the Network AI Agent.

This module contains the NetworkAgentConfig class that manages all
configuration variables used throughout the application.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from dotenv import load_dotenv


@dataclass
class NetworkAgentConfig:
    """Configuration for network automation agent."""

    # Mapping: ENV_VAR → (attribute_name, type, default_or_required)
    _ENV_MAPPING: ClassVar = {
        "GROQ_API_KEY": ("groq_api_key", str, None),  # Required during validation
        "LLM_MODEL_NAME": ("llm_model_name", str, "openai/gpt-oss-120b"),
        "LLM_TEMPERATURE": (
            "llm_temperature",
            float,
            0.0,
        ),  # Changed to 0.0 for deterministic output in Linear Pipeline
        "LLM_MAX_TOKENS": ("llm_max_tokens", int, 2048),
        "MAX_HISTORY_TOKENS": (
            "max_history_tokens",
            int,
            20000,
        ),  # Updated from 2000 to 20000 to handle network configs
        "NUM_WORKERS": ("num_workers", int, 20),
        "NETMIKO_TIMEOUT": ("netmiko_timeout", int, 30),
        "NETMIKO_CONN_TIMEOUT": ("netmiko_conn_timeout", int, 10),
        "NETMIKO_SESSION_TIMEOUT": ("netmiko_session_timeout", int, 60),
        "LOG_LEVEL": ("log_level", str, "INFO"),
        "LOG_FILE": ("log_file", str, "network_agent.log"),
        "INVENTORY_PATH": ("inventory_path", str, "hosts.yaml"),
        "GROUPS_FILE": ("groups_file", str, "groups.yaml"),
    }

    # Configuration fields
    groq_api_key: str = None  # Will be validated separately
    llm_model_name: str = "openai/gpt-oss-120b"
    llm_temperature: float = 0.0  # Changed from 0.7 to 0.0 for production precision
    llm_max_tokens: int = 2048
    max_history_tokens: int = 20000  # Updated from 2000 to 20000 to handle network configs
    num_workers: int = 20
    netmiko_timeout: int = 30
    netmiko_conn_timeout: int = 10
    netmiko_session_timeout: int = 60
    log_level: str = "INFO"
    log_file: str = "network_agent.log"
    inventory_path: str = "hosts.yaml"
    groups_file: str = "groups.yaml"

    # Computed paths
    base_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    log_skip_modules: list[str] = field(
        default_factory=lambda: [
            "httpcore",
            "httpx",
            "markdown_it",
            "groq._base_client",
        ]
    )

    @classmethod
    def from_env(cls, env_file: str = ".env") -> "NetworkAgentConfig":
        """Load configuration from environment variables."""
        if os.path.exists(env_file):
            load_dotenv(env_file)

        kwargs = {}
        for env_var, (attr_name, var_type, default_val) in cls._ENV_MAPPING.items():
            value = os.getenv(env_var)

            if value is None:
                if (
                    default_val is None and env_var == "GROQ_API_KEY"
                ):  # Special handling for API key
                    kwargs[attr_name] = None
                elif default_val is None:  # Other required field
                    raise RuntimeError(
                        f"Required config '{env_var}' not found in environment or .env file"
                    )
                else:  # Optional field with default
                    kwargs[attr_name] = default_val
            else:
                if var_type is int:
                    kwargs[attr_name] = int(value)
                elif var_type is float:
                    kwargs[attr_name] = float(value)
                else:  # str or other type
                    kwargs[attr_name] = value

        return cls(**kwargs)

    @classmethod
    def load(cls) -> "NetworkAgentConfig":
        """Legacy method for backward compatibility."""
        return cls.from_env()

    def validate(self) -> None:
        """Validate required configuration is present.

        Raises:
            RuntimeError: If required configuration is missing
        """
        if not self.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY environment variable is required. "
                "Please set it in your .env file or environment."
            )
