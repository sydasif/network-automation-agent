"""Module for setting up the LLM client for the network automation agent.

This module provides functionality to initialize and configure the LLM client
using the Groq API. It handles API key management and creates the appropriate
language model instance for the agent.

The module is designed specifically for network automation tasks, where
deterministic and accurate responses are crucial for proper command
interpretation and device management.
"""

import os

from langchain_groq import ChatGroq


def create_llm(api_key: str | None = None):
    """Creates and configures a ChatGroq LLM instance for the network agent.

    Initializes a ChatGroq language model optimized for network automation tasks.
    The temperature is set to a low value (0.2) to ensure consistent and
    deterministic responses, which is crucial for correctly interpreting
    commands and device names in an automation context.

    The function supports both direct API key parameter and environment
    variable configuration for flexibility in different deployment scenarios.

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

    model_name = os.getenv("LLM_MODEL_NAME", "openai/gpt-oss-20b")

    # A lower temperature is crucial for an automation agent to ensure it
    # correctly interprets commands and device names, reducing the risk of
    # "hallucinations" or unpredictable behavior.
    llm = ChatGroq(temperature=0.2, model_name=model_name, api_key=api_key)

    return llm
