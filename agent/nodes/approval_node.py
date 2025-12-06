"""Approval node for human-in-the-loop config changes."""

import logging
from typing import Any

from langchain_core.messages import ToolMessage
from langgraph.types import interrupt

from agent.nodes.base_node import AgentNode
from agent.state import RESUME_APPROVED

logger = logging.getLogger(__name__)


class ApprovalNode(AgentNode):
    """Request user approval for configuration changes."""

    def execute(self, state: dict[str, Any]) -> dict[str, Any] | None:
        """Request approval from user for config changes."""
        messages = state.get("messages", [])
        if not messages:
            return None

        last_msg = messages[-1]

        # Check for tool calls
        if not hasattr(last_msg, "tool_calls") or not last_msg.tool_calls:
            return None

        # Identify sensitive calls (config_command)
        sensitive_calls = [tc for tc in last_msg.tool_calls if tc["name"] == "config_command"]

        if not sensitive_calls:
            return None

        # Interrupt workflow and wait for user decision on the BATCH of calls
        decision = interrupt({"type": "approval_request", "tool_calls": sensitive_calls})

        if decision == RESUME_APPROVED:
            logger.info(f"User approved batch of {len(sensitive_calls)} calls")
            return None

        # User denied - generate denial messages for ALL calls to maintain state consistency
        logger.info("User denied configuration batch")
        denial_messages = [
            ToolMessage(
                tool_call_id=tc["id"],
                content=f"❌ User denied permission for operation: {tc['name']}",
            )
            for tc in sensitive_calls
        ]

        return {"messages": denial_messages}
