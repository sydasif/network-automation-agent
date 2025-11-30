"""Agent routing logic for the Network AI Agent.

This module contains the routing functions that determine the flow of the
LangGraph workflow based on the state and tool calls.
"""

from typing import Literal

from langchain_core.messages import ToolMessage
from langgraph.graph import END

from agent.nodes import NODE_APPROVAL, NODE_EXECUTE, NODE_PLANNER, NODE_UNDERSTAND, State
from tools.config import config_command
from tools.plan import plan_task
from tools.response import respond


def route_tools(state: State) -> Literal[NODE_EXECUTE, NODE_APPROVAL, NODE_PLANNER, "end"]:
    """Route the workflow based on the tool called in the last message.

    Determines whether the workflow should proceed to execution or approval
    based on whether the tool called is a configuration command that requires
    human approval.

    Args:
        state: The current state of the workflow containing messages.

    Returns:
        The next node in the workflow: NODE_EXECUTE, NODE_APPROVAL, or END.
    """
    last_message = state["messages"][-1]

    # If no tool calls are present, end the workflow
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return END

    tool_name = last_message.tool_calls[0]["name"]

    # DRY: Use the actual tool name property instead of a hardcoded string.
    # If the tool name changes in tools/commands.py, this logic stays valid.
    # Route to approval for config commands that modify device configuration
    if tool_name == config_command.name:
        return NODE_APPROVAL

    if tool_name == plan_task.name:
        return NODE_PLANNER

    if tool_name == respond.name:
        return END

    # For other commands (like show commands), execute directly
    return NODE_EXECUTE


def route_approval(state: State) -> Literal[NODE_EXECUTE, NODE_UNDERSTAND]:
    """Route the workflow after the approval node based on user decision.

    If the user denied approval (ToolMessage injected), route back to Understand
    to explain why the action was denied. If approved, proceed to Execute.

    Args:
        state: The current state of the workflow containing messages.

    Returns:
        The next node in the workflow: NODE_EXECUTE or NODE_UNDERSTAND.
    """
    last_message = state["messages"][-1]

    # If the last message is a ToolMessage, it means we injected a "Denied" response
    # This happens when the user denies a configuration change request
    if isinstance(last_message, ToolMessage):
        return NODE_UNDERSTAND

    # If no ToolMessage is present, the approval was granted, proceed to execute
    return NODE_EXECUTE
