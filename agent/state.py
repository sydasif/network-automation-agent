"""State management for the agent workflow.

This module defines the State structure used throughout
the LangGraph workflow with extended fields.
"""

from typing import Annotated, List, Optional, Dict, Any
from typing_extensions import TypedDict

from langgraph.graph import add_messages


class State(TypedDict):
    """State structure for the agent workflow with extended fields.

    The state contains the conversation history as a list of messages
    and additional fields for enhanced functionality.
    """
    messages: Annotated[List, add_messages]
    device_status: Optional[Dict[str, Any]]
    current_session: Optional[str]
    approval_context: Optional[Dict[str, Any]]
    execution_metadata: Optional[Dict[str, Any]]


# Node name constants for workflow graph
NODE_APPROVAL = "approval"
NODE_EXECUTE = "execute"
NODE_UNDERSTANDING = "understanding"
NODE_RESPONSE = "response"

# Resume constants for approval node
RESUME_APPROVED = "approved"
RESUME_DENIED = "denied"