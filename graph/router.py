from typing import Literal, TypedDict, Annotated
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langchain_core.messages import ToolMessage

# Import the new nodes
from graph.nodes import (
    understand_node,
    approval_node,
    read_tool_node,
    write_tool_node,
    respond_node,
)


class State(TypedDict):
    messages: Annotated[list, add_messages]
    # 'results' is no longer strictly needed as ToolNode stores results in 'messages'
    # but you can keep it if you have other uses.


def route_tools(state: State) -> Literal["execute_read", "approval", "respond"]:
    """Decides where to go after 'understand'."""
    last_message = state["messages"][-1]

    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return "respond"

    tool_name = last_message.tool_calls[0]["name"]

    if tool_name == "config_command":
        return "approval"  # Dangerous -> Go to Gatekeeper

    return "execute_read"  # Safe -> Go to Execution


def route_approval(state: State) -> Literal["execute_write", "respond"]:
    """Decides where to go after 'approval'."""
    last_message = state["messages"][-1]

    # If the last message is a ToolMessage, it means we DENIED the request
    # (because approval_node injected a denial message).
    if isinstance(last_message, ToolMessage):
        return "respond"

    # Otherwise (if it's still the AIMessage), we APPROVED it.
    return "execute_write"


def create_graph():
    workflow = StateGraph(State)

    workflow.add_node("understand", understand_node)
    workflow.add_node("approval", approval_node)
    workflow.add_node("execute_read", read_tool_node)  # Native ToolNode
    workflow.add_node("execute_write", write_tool_node)  # Native ToolNode
    workflow.add_node("respond", respond_node)

    workflow.set_entry_point("understand")

    # 1. From Understand -> Read, Approval, or Respond
    workflow.add_conditional_edges(
        "understand",
        route_tools,
        {
            "execute_read": "execute_read",
            "approval": "approval",
            "respond": "respond",
        },
    )

    # 2. From Approval -> Write (if approved) or Respond (if denied)
    workflow.add_conditional_edges(
        "approval", route_approval, {"execute_write": "execute_write", "respond": "respond"}
    )

    # 3. Standard edges
    workflow.add_edge("execute_read", "respond")
    workflow.add_edge("execute_write", "respond")
    workflow.add_edge("respond", END)

    return workflow.compile(checkpointer=MemorySaver())
