"""Context manager node for conversation history management.

This module provides the ContextManagerNode class that handles
conversation history trimming and context window management.
"""

import logging
from typing import Any

from langchain_core.messages import SystemMessage, trim_messages
from langchain_core.messages.utils import count_tokens_approximately

from agent.nodes.base_node import AgentNode
from agent.prompts import NetworkAgentPrompts
from core.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class ContextManagerNode(AgentNode):
    """Manages conversation history and context window.

    This node handles message trimming to fit within context windows
    and maintains conversation continuity.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        max_history_tokens: int = 3500,
    ):
        """Initialize the context manager node.

        Args:
            llm_provider: LLMProvider instance
            max_history_tokens: Maximum tokens for conversation history
        """
        super().__init__(llm_provider)
        self._max_history_tokens = max_history_tokens

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Manage conversation history and context window.

        Args:
            state: Current workflow state

        Returns:
            Updated state with trimmed messages
        """
        messages = state.get("messages", [])

        # Trim messages to fit within context window
        trimmed_msgs = self._trim_messages(messages)

        return {"messages": trimmed_msgs}

    def _trim_messages(self, messages: list) -> list:
        """Trim messages to fit within context window.

        Args:
            messages: List of messages

        Returns:
            Trimmed list of messages
        """
        try:
            trimmed_msgs = trim_messages(
                messages,
                max_tokens=self._max_history_tokens,
                strategy="last",
                token_counter=count_tokens_approximately,
                start_on="human",
                include_system=False,
                allow_partial=False,
            )

            # Log if trimming occurred
            if len(messages) > len(trimmed_msgs):
                original_tokens = count_tokens_approximately(messages)
                trimmed_tokens = count_tokens_approximately(trimmed_msgs)

                logger.info(
                    f"Context trimmed: {len(messages)} messages (~{original_tokens} tokens) "
                    f"→ {len(trimmed_msgs)} messages (~{trimmed_tokens} tokens)"
                )

                # Summarize dropped messages
                dropped_count = len(messages) - len(trimmed_msgs)
                if dropped_count > 0:
                    dropped_msgs = messages[:dropped_count]
                    summary = self._summarize_messages(dropped_msgs)

                    summary_msg = SystemMessage(
                        content=f"Previous Conversation Summary:\n{summary}"
                    )
                    trimmed_msgs = [summary_msg] + trimmed_msgs
                    logger.info("Added conversation summary for dropped messages.")

            return trimmed_msgs

        except Exception as trim_error:
            logger.warning(
                f"Message trimming failed ({type(trim_error).__name__}): {trim_error}. "
                "Using fallback strategy."
            )
            # Fallback: keep last 10 messages
            return messages[-10:] if len(messages) > 10 else messages

    def _summarize_messages(self, messages: list) -> str:
        """Summarize messages using LLM.

        Args:
            messages: List of messages to summarize

        Returns:
            Summary string
        """
        llm = self._get_llm()
        prompt = f"{NetworkAgentPrompts.summary_system}\n\nMessages:\n"
        for msg in messages:
            role = "User" if hasattr(msg, "role") and msg.role != "assistant" else "User"
            if hasattr(msg, "content"):
                prompt += f"{role}: {msg.content}\n"

        response = llm.invoke(prompt)
        return response.content
