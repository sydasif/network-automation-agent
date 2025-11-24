"""agent/router.py: Logic for conditional edges in the graph."""

from typing import Literal

from langchain_core.messages import ToolMessage
from langgraph.graph import END

from agent.nodes import NODE_APPROVAL, NODE_EXECUTE, NODE_UNDERSTAND, State
from tools.commands import config_command


def route_tools(state: State) -> Literal[NODE_EXECUTE, NODE_APPROVAL, "end"]:
    """
    Router checks if the tool call requires human approval.
    """
    last_message = state["messages"][-1]

    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return END

    tool_name = last_message.tool_calls[0]["name"]

    # DRY: Use the actual tool name property instead of a hardcoded string.
    # If the tool name changes in tools/commands.py, this logic stays valid.
    if tool_name == config_command.name:
        return NODE_APPROVAL

    return NODE_EXECUTE


def route_approval(state: State) -> Literal[NODE_EXECUTE, NODE_UNDERSTAND]:
    """
    Determines next step after approval node.
    If the user denied (ToolMessage injected), go back to Understand to explain why.
    If approved (no output/None), go to Execute.
    """
    last_message = state["messages"][-1]

    # If the last message is a ToolMessage, it means we injected a "Denied" response
    if isinstance(last_message, ToolMessage):
        return NODE_UNDERSTAND

    return NODE_EXECUTE
