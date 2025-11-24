"""Module for setting up the LLM client for the network automation agent."""

from langchain_groq import ChatGroq

from settings import GROQ_API_KEY, LLM_MODEL_NAME, LLM_TEMPERATURE  # <--- IMPORTED


def create_llm(api_key: str | None = None):
    """Creates and configures a ChatGroq LLM instance."""
    # Use passed key or fallback to settings
    final_api_key = api_key or GROQ_API_KEY

    if not final_api_key:
        raise RuntimeError("GROQ_API_KEY not set in environment")

    llm = ChatGroq(temperature=LLM_TEMPERATURE, model_name=LLM_MODEL_NAME, api_key=final_api_key)

    return llm
