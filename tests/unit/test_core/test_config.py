"""Unit tests for NetworkAgentConfig."""

import os
from unittest.mock import patch

import pytest

from core.config import NetworkAgentConfig


def test_config_load_defaults():
    """Test loading configuration with defaults."""
    # Mock environment variables to ensure clean state
    with patch.dict(os.environ, {"GROQ_API_KEY": "test_key"}, clear=True):
        # Mock load_dotenv to prevent reading actual .env file
        with patch("core.config.load_dotenv"):
            config = NetworkAgentConfig()

            assert config.groq_api_key == "test_key"
            assert config.llm_model_name == "openai/gpt-oss-20b"
            assert config.llm_temperature == 0.0
            assert config.num_workers == 20
            assert config.netmiko_timeout == 30


def test_config_load_env_overrides():
    """Test loading configuration with environment variable overrides."""
    env_vars = {
        "GROQ_API_KEY": "test_key",
        "LLM_MODEL_NAME": "custom-model",
        "LLM_TEMPERATURE": "0.5",
        "NUM_WORKERS": "10",
        "NETMIKO_TIMEOUT": "60",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        with patch("core.config.load_dotenv"):
            config = NetworkAgentConfig()

            assert config.llm_model_name == "custom-model"
            assert config.llm_temperature == 0.5
            assert config.num_workers == 10
            assert config.netmiko_timeout == 60


def test_config_validation_missing_api_key():
    """Test validation fails when API key is missing."""
    with patch.dict(os.environ, {}, clear=True):
        with patch("core.config.load_dotenv"):
            # Should not raise on init
            config = NetworkAgentConfig()

            # Should raise RuntimeError on validate()
            with pytest.raises(
                RuntimeError, match="GROQ_API_KEY environment variable is required"
            ):
                config.validate()


def test_config_log_skip_modules():
    """Test parsing of log skip modules."""
    with patch.dict(os.environ, {"GROQ_API_KEY": "test_key"}, clear=True):
        config = NetworkAgentConfig()
        # Check default list
        assert "httpcore" in config.log_skip_modules
        assert "httpx" in config.log_skip_modules
