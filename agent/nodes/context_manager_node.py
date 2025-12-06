"""Context manager node that passes state through without modification."""

import logging
from typing import Any

from agent.nodes.base_node import AgentNode
from core.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class ContextManagerNode(AgentNode):
    """Passes state through without modification to avoid message duplication."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        max_history_tokens: int = 1500,
    ):
        super().__init__(llm_provider)
        self._max_history_tokens = max_history_tokens

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Pass state through without modification - local sanitization in other nodes."""
        # Log state size for debugging but don't modify messages
        messages = state.get("messages", [])
        logger.debug(f"ContextManagerNode: State has {len(messages)} messages")
        return {}  # Return empty dict to avoid message duplication
