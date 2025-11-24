"""agent/router.py: Logic for conditional edges in the graph."""

from typing import Literal

from langchain_core.messages import ToolMessage
from langgraph.graph import END

from agent.nodes import NODE_APPROVAL, NODE_EXECUTE, NODE_UNDERSTAND, State


def route_tools(state: State) -> Literal[NODE_EXECUTE, NODE_APPROVAL, "end"]:
    last_message = state["messages"][-1]

    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return END

    tool_name = last_message.tool_calls[0]["name"]
    if tool_name == "config_command":
        return NODE_APPROVAL

    return NODE_EXECUTE


def route_approval(state: State) -> Literal[NODE_EXECUTE, NODE_UNDERSTAND]:
    last_message = state["messages"][-1]
    if isinstance(last_message, ToolMessage):
        return NODE_UNDERSTAND
    return NODE_EXECUTE
