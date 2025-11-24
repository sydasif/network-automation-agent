"""Module for setting up the LLM client for the network automation agent."""

import os

from langchain_groq import ChatGroq


def create_llm(api_key: str | None = None):
    """Creates and configures a ChatGroq LLM instance for the network agent."""
    api_key = api_key or os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set in environment")

    model_name = os.getenv("LLM_MODEL_NAME", "openai/gpt-oss-20b")

    llm = ChatGroq(temperature=0.2, model_name=model_name, api_key=api_key)

    return llm
