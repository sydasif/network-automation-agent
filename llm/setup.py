import os

from langchain_groq import ChatGroq


def create_llm(api_key: str | None = None):
    api_key = api_key or os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set in environment")

    llm = ChatGroq(temperature=0, model_name="openai/gpt-oss-20b", api_key=api_key)
    return llm
