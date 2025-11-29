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

LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "openai/gpt-oss-20b")
"""Primary LLM model to use for processing requests."""

LLM_TEMPERATURE = 0.0
"""Temperature setting for the LLM model. 0.0 is best for tool use."""

MAX_HISTORY_TOKENS = 3500
"""Maximum tokens for conversation history (reserving ~500 tokens for system prompt and response buffer)."""
