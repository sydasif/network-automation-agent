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

LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "openai/gpt-oss-20b")
"""Name of the LLM model to use for processing requests."""

LLM_TEMPERATURE = 0.2
"""Temperature setting for the LLM model."""

# KISS: Simple message count limit instead of token counting
MAX_HISTORY_MESSAGES = 20
"""Maximum number of messages to keep in history for context."""

# Network Device Settings
DEVICE_TIMEOUT = 30
"""Timeout value in seconds for device connections."""
