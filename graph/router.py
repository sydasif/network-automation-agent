"""Defines the state graph and routing logic."""

from typing import Annotated, Any, Literal, TypedDict
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from graph.nodes import understand_node, execute_read_node, execute_write_node, respond_node


class State(TypedDict):
    messages: Annotated[list, add_messages]
    results: dict[str, Any]


def route_tools(state: State) -> Literal["execute_read", "execute_write", "respond"]:
    last_message = state["messages"][-1]
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return "respond"

    tool_name = last_message.tool_calls[0]["name"]
    return "execute_write" if tool_name == "config_command" else "execute_read"


def create_graph():
    workflow = StateGraph(State)

    workflow.add_node("understand", understand_node)
    workflow.add_node("execute_read", execute_read_node)
    workflow.add_node("execute_write", execute_write_node)
    workflow.add_node("respond", respond_node)

    workflow.set_entry_point("understand")

    workflow.add_conditional_edges(
        "understand",
        route_tools,
        {
            "execute_read": "execute_read",
            "execute_write": "execute_write",
            "respond": "respond",
        },
    )

    workflow.add_edge("execute_read", "respond")
    workflow.add_edge("execute_write", "respond")
    workflow.add_edge("respond", END)

    # No static interrupt needed! The node calls interrupt() dynamically.
    return workflow.compile(checkpointer=MemorySaver())
