"""Approval node for human-in-the-loop config changes.

This module provides the ApprovalNode class that requests user
approval before applying configuration changes.
"""

import logging
from typing import Any

from langchain_core.messages import ToolMessage
from langgraph.types import interrupt

from agent.nodes.base_node import AgentNode

logger = logging.getLogger(__name__)

# Node constants
RESUME_APPROVED = "approved"
RESUME_DENIED = "denied"


class ApprovalNode(AgentNode):
    """Request user approval for configuration changes.

    This node interrupts workflow execution and waits for user
    decision before proceeding with configuration changes.
    """

    def execute(self, state: dict[str, Any]) -> dict[str, Any] | None:
        """Request approval from user for config changes.

        Args:
            state: Current workflow state

        Returns:
            None if approved, or state with denial message if rejected
        """
        messages = state.get("messages", [])
        if not messages:
            return None

        last_msg = messages[-1]

        # Check if there are tool calls to approve
        if not hasattr(last_msg, "tool_calls") or not last_msg.tool_calls:
            return None

        tool_call = last_msg.tool_calls[0]

        # Interrupt workflow and wait for user decision
        decision = interrupt({"type": "approval_request", "tool_call": tool_call})

        if decision == RESUME_APPROVED:
            logger.info(f"User approved: {tool_call['name']}")
            return None

        # User denied the configuration change
        logger.info(f"User denied: {tool_call['name']}")
        return {
            "messages": [
                ToolMessage(
                    tool_call_id=tool_call["id"],
                    content=f"❌ User denied permission: {tool_call['name']}",
                )
            ],
        }
