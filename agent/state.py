"""State management for the agent workflow.

This module defines the State structure used throughout
the LangGraph workflow.
"""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class State(TypedDict):
    """State structure for the agent workflow.

    The state contains the conversation history as a list of messages.
    LangGraph's add_messages reducer handles message updates automatically.
    """

    messages: Annotated[list, add_messages]


# Node name constants for workflow graph
NODE_PLANNER = "planner"
NODE_APPROVAL = "approval"
NODE_EXECUTE = "execute"
NODE_UNDERSTANDING = "understanding"
NODE_RESPONSE = "response"  # <--- Added this

# Resume constants for approval node
RESUME_APPROVED = "approved"
RESUME_DENIED = "denied"
