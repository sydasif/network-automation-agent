"""Message management for optimizing LLM token usage and enforcing limits."""

import logging
from typing import List

import tiktoken
from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    ToolMessage,
)

logger = logging.getLogger(__name__)


class MessageManager:
    """Manages all message handling: token counting, compression, and limits."""

    def __init__(
        self, max_tokens: int = 100000, max_message_count: int = 40, model_name: str = "gpt-4"
    ):
        """Initialize message manager.

        Args:
            max_tokens: Maximum tokens allowed in context (default: 100000)
            max_message_count: Maximum number of messages in context (default: 40)
            model_name: Model name for encoding selection (default: gpt-4 for cl100k_base)
        """
        self.max_tokens = max_tokens
        self.max_message_count = max_message_count
        try:
            self._encoding = tiktoken.encoding_for_model(model_name)
        except KeyError:
            # Fallback to cl100k_base which is standard for modern LLMs (GPT-4, Llama 3)
            self._encoding = tiktoken.get_encoding("cl100k_base")

    def prepare_for_llm(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """Prepare messages for LLM by applying all safety measures.

        Args:
            messages: Input messages from conversation history

        Returns:
            Processed messages ready for LLM
        """
        # First enforce message count limit
        limited_messages = self._enforce_message_limit(messages)

        # Check if token limit is satisfied
        if self._is_token_safe(limited_messages):
            return limited_messages

        # If token limit exceeded, compress history
        compressed = self._compress_history(limited_messages)

        # If still not safe after compression, log warning but return anyway
        if not self._is_token_safe(compressed):
            logger.warning(
                f"Messages still exceed token limit after compression. "
                f"Token count: {self.count_tokens(compressed)}, Limit: {self.max_tokens}"
            )

        return compressed

    def _enforce_message_limit(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """Keep only last N messages to enforce message count limit."""
        if len(messages) <= self.max_message_count:
            return messages

        # Separate system messages which should always be preserved
        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        other_msgs = [m for m in messages if not isinstance(m, SystemMessage)]

        # Keep the most recent non-system messages up to the limit
        remaining_count = self.max_message_count - len(system_msgs)
        if remaining_count <= 0:
            # If system messages already fill the limit, keep only them
            return system_msgs

        recent_msgs = other_msgs[-remaining_count:]
        return system_msgs + recent_msgs

    def _is_token_safe(self, messages: List[BaseMessage]) -> bool:
        """Check if message tokens are under limit."""
        token_count = self.count_tokens(messages)
        return token_count < self.max_tokens

    def _compress_history(
        self, messages: List[BaseMessage], keep_last: int = 6, max_tool_output: int = 100
    ) -> List[BaseMessage]:
        """Compress older messages while preserving the most recent context.

        Strategy:
        1. Always keep SystemMessages.
        2. Keep the last `keep_last` messages fully intact.
        3. For older messages:
           - Keep Human/AI messages (conversation flow).
           - Truncate ToolMessages (bulk data) to save space.
        """
        if not messages:
            return []

        # 1. Separate System Messages (Always keep)
        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        other_msgs = [m for m in messages if not isinstance(m, SystemMessage)]

        # 2. Split into "Old" and "Recent"
        if len(other_msgs) <= keep_last:
            return system_msgs + other_msgs

        recent_msgs = other_msgs[-keep_last:]
        old_msgs = other_msgs[:-keep_last]

        # 3. Compress Old Messages
        compressed_old = []
        for msg in old_msgs:
            if isinstance(msg, ToolMessage):
                # Compress massive tool outputs
                content_str = str(msg.content)
                if len(content_str) > max_tool_output:
                    new_content = (
                        f"{content_str[:max_tool_output]}...\n"
                        f"[Output truncated. Original length: {len(content_str)} chars]"
                    )
                    # Create a copy with truncated content
                    compressed_msg = ToolMessage(
                        content=new_content,
                        tool_call_id=msg.tool_call_id,
                        name=msg.name,
                        status=msg.status,
                    )
                    compressed_old.append(compressed_msg)
                else:
                    compressed_old.append(msg)
            else:
                # Keep Human and AI messages intact so the "story" makes sense
                compressed_old.append(msg)

        # 4. Reassemble
        return system_msgs + compressed_old + recent_msgs

    def count_tokens(self, messages: List[BaseMessage]) -> int:
        """Count total tokens in a list of messages.

        Args:
            messages: List of LangChain messages

        Returns:
            Total token count
        """
        total = 0
        for msg in messages:
            content = msg.content
            if isinstance(content, str):
                total += len(self._encoding.encode(content))
            elif isinstance(content, list):
                # Handle multimodal content type if present
                for part in content:
                    if isinstance(part, dict) and "text" in part:
                        total += len(self._encoding.encode(part["text"]))

        # Add per-message overhead (approx 3 tokens per msg for role/formatting)
        total += len(messages) * 3
        return total
