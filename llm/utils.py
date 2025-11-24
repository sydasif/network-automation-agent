from typing import List

from langchain_core.messages import BaseMessage, trim_messages

from settings import LLM_MAX_TOKENS


def manage_chat_history(messages: List[BaseMessage]) -> List[BaseMessage]:
    """
    Trims the chat history to fit within the configured token limit.
    Ensures the context always starts with a Human message and keeps the most recent interactions.
    """
    return trim_messages(
        messages,
        max_tokens=LLM_MAX_TOKENS,
        strategy="last",
        token_counter=len,  # In production, you might use a real tokenizer here
        start_on="human",
        end_on=("human", "ai"),
        include_system=False,
    )
