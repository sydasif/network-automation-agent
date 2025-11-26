"""Configuration settings for the Network AI Agent.

This module contains all the configuration variables used throughout the application,
including paths, LLM settings, and network device parameters.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Automatically load .env file from the project root
load_dotenv()

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
"""The base directory of the project."""

INVENTORY_HOST_FILE = BASE_DIR / "hosts.yaml"
"""Path to the hosts.yaml inventory file."""

INVENTORY_GROUP_FILE = BASE_DIR / "groups.yaml"
"""Path to the groups.yaml inventory file."""

# LLM Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
"""API key for GROQ LLM service."""

# Primary and fallback LLM models
# The fallback mechanism will try models in order when the primary model fails
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "openai/gpt-oss-20b")
"""Primary LLM model to use for processing requests."""

# Fallback models in order of preference
# Remove the primary model from fallbacks to avoid redundant attempts
fallback_models_raw = [
    model.strip()
    for model in os.getenv("LLM_FALLBACK_MODELS", "openai/gpt-oss-120b,qwen/qwen3-32b").split(",")
    if model.strip()
]
LLM_FALLBACK_MODELS = [model for model in fallback_models_raw if model != LLM_MODEL_NAME]
"""List of fallback LLM models to use when primary model fails. Models are tried in order."""

LLM_TEMPERATURE = 0.0
"""Temperature setting for the LLM model. 0.0 is best for tool use."""

# Reduce history to save tokens
MAX_HISTORY_MESSAGES = 10
"""Maximum number of messages to keep in history for context."""

# Network Device Settings
DEVICE_TIMEOUT = 30
"""Timeout value in seconds for device connections."""
