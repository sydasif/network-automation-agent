"""Configuration settings for the Network AI Agent.

This module contains all the configuration variables used throughout the application,
including LLM settings and other application parameters.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Automatically load .env file from the project root
load_dotenv()

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
"""The base directory of the project."""

# LLM Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
"""API key for GROQ LLM service."""

LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "openai/gpt-oss-120b")
"""Primary LLM model to use for processing requests."""

LLM_TEMPERATURE = 0.0
"""Temperature setting for the LLM model. 0.0 is best for tool use."""

MAX_HISTORY_TOKENS = 3500
"""Maximum tokens for conversation history (reserving ~500 tokens for system prompt and response buffer)."""

# Logging Configuration
LOG_SKIP_MODULES = [
    "httpcore",
    "httpx",
    "markdown_it",
    "groq._base_client",
]
"""List of module names whose logs should be skipped to keep UI clean."""

# Nornir Configuration
NUM_WORKERS = int(os.getenv("NUM_WORKERS", "20"))
"""Number of parallel workers for Nornir task execution."""

NETMIKO_TIMEOUT = int(os.getenv("NETMIKO_TIMEOUT", "30"))
"""Default timeout for Netmiko commands in seconds."""

NETMIKO_CONN_TIMEOUT = int(os.getenv("NETMIKO_CONN_TIMEOUT", "10"))
"""Connection timeout for Netmiko in seconds."""

NETMIKO_SESSION_TIMEOUT = int(os.getenv("NETMIKO_SESSION_TIMEOUT", "60"))
"""Session timeout for Netmiko in seconds."""
