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

# SWITCHED TO 8B INSTANT TO AVOID RATE LIMITS & IMPROVE SPEED
# We prefer the env var, but if you are hitting limits, please unset LLM_MODEL_NAME in .env
# or change it to "llama-3.1-8b-instant"
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "llama-3.1-8b-instant")
"""Name of the LLM model to use for processing requests."""

LLM_TEMPERATURE = 0.0
"""Temperature setting for the LLM model. 0.0 is best for tool use."""

# Reduce history to save tokens
MAX_HISTORY_MESSAGES = 10
"""Maximum number of messages to keep in history for context."""

# Network Device Settings
DEVICE_TIMEOUT = 30
"""Timeout value in seconds for device connections."""
