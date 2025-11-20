"""Module for setting up the LLM client for the network automation agent.

This module provides functionality to initialize and configure the LLM client
using the Groq API. It handles API key management and creates the appropriate
language model instance for the agent.
"""

import os

from langchain_groq import ChatGroq


def create_llm(api_key: str | None = None):
    """Creates and configures a ChatGroq LLM instance for the network agent.

    This function initializes a ChatGroq language model with a temperature of 0
    to ensure consistent and deterministic responses for network automation tasks.
    It retrieves the API key from the provided parameter or environment variable.

    Args:
        api_key: Optional API key for Groq. If not provided, the function
                will attempt to read it from the GROQ_API_KEY environment variable.

    Returns:
        Configured ChatGroq instance ready for use in the network automation workflow.

    Raises:
        RuntimeError: If no API key is provided and GROQ_API_KEY environment variable is not set.
    """
    api_key = api_key or os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set in environment")

    llm = ChatGroq(temperature=0.7, model_name="openai/gpt-oss-20b", api_key=api_key)
    return llm
