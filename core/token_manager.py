"""Token manager for enforcing strict token limits.

This module provides the TokenManager class that accurately counts
tokens using tiktoken and provides safety checks to prevent
Rate Limit Exceeded (413) errors from the LLM API.
"""

import logging

import tiktoken
from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages token counting and limit enforcement."""

    # With 300k TPM models, we can increase the safety buffer
    # This prevents massive single-request overflows while still allowing large contexts
    MAX_REQUEST_TOKENS = 100000

    def __init__(self, model_name: str = "gpt-4"):
        """Initialize token manager.

        Args:
            model_name: Model name for encoding selection (default: gpt-4 for cl100k_base)
        """
        try:
            self._encoding = tiktoken.encoding_for_model(model_name)
        except KeyError:
            # Fallback to cl100k_base which is standard for modern LLMs (GPT-4, Llama 3)
            self._encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Count tokens in a text string.

        Args:
            text: Input text

        Returns:
            Number of tokens
        """
        if not text:
            return 0
        return len(self._encoding.encode(text))

    def count_messages_tokens(self, messages: list[BaseMessage]) -> int:
        """Count total tokens in a list of messages.

        This enables accurate estimation of the full payload including
        system messages and tool outputs.

        Args:
            messages: List of LangChain messages

        Returns:
            Total token count
        """
        total = 0
        for msg in messages:
            content = msg.content
            if isinstance(content, str):
                total += self.count_tokens(content)
            elif isinstance(content, list):
                # Handle multimodal content type if present
                for part in content:
                    if isinstance(part, dict) and "text" in part:
                        total += self.count_tokens(part["text"])

        # Add per-message overhead (approx 3 tokens per msg for role/formatting)
        total += len(messages) * 3
        return total

    def check_safe_to_send(self, messages: list[BaseMessage]) -> bool:
        """Check if message payload is safe to send within limits.

        Args:
            messages: List of messages to check

        Returns:
            True if safe, False if exceeds limit
        """
        total_tokens = self.count_messages_tokens(messages)

        if total_tokens > self.MAX_REQUEST_TOKENS:
            logger.warning(
                f"Token limit exceeded! Request: {total_tokens} tokens, "
                f"Limit: {self.MAX_REQUEST_TOKENS}"
            )
            return False

        logger.debug(f"Request safe: {total_tokens} tokens")
        return True
