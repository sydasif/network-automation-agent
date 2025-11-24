from typing import Annotated, Literal, TypedDict

from langchain_core.messages import ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

# Import the new nodes
from graph.nodes import (
    approval_node,
    read_tool_node,
    respond_node,
    understand_node,
    write_tool_node,
)


class State(TypedDict):
    messages: Annotated[list, add_messages]


def route_tools(state: State) -> Literal["execute_read", "approval", "respond"]:
    """Decides where to go after 'understand'."""
    last_message = state["messages"][-1]

    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return "respond"

    tool_name = last_message.tool_calls[0]["name"]

    if tool_name == "config_command":
        return "approval"

    return "execute_read"


def route_approval(state: State) -> Literal["execute_write", "respond"]:
    """Decides where to go after 'approval'."""
    last_message = state["messages"][-1]

    if isinstance(last_message, ToolMessage):
        return "respond"

    return "execute_write"


def create_graph():
    workflow = StateGraph(State)

    workflow.add_node("understand", understand_node)
    workflow.add_node("approval", approval_node)
    workflow.add_node("execute_read", read_tool_node)
    workflow.add_node("execute_write", write_tool_node)
    workflow.add_node("respond", respond_node)

    workflow.set_entry_point("understand")

    workflow.add_conditional_edges(
        "understand",
        route_tools,
        {
            "execute_read": "execute_read",
            "approval": "approval",
            "respond": "respond",
        },
    )

    workflow.add_conditional_edges(
        "approval", route_approval, {"execute_write": "execute_write", "respond": "respond"}
    )

    workflow.add_edge("execute_read", "respond")
    workflow.add_edge("execute_write", "respond")
    workflow.add_edge("respond", END)

    return workflow.compile(checkpointer=MemorySaver())
