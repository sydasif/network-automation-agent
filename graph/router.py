from typing import Annotated, Literal, TypedDict

from langchain_core.messages import ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

# UPDATED IMPORTS
from graph.consts import (
    NODE_APPROVAL,
    NODE_EXECUTE,
    NODE_RESPOND,
    NODE_UNDERSTAND,
)
from graph.nodes import (
    approval_node,
    execute_node,  # Single node
    respond_node,
    understand_node,
)


class State(TypedDict):
    messages: Annotated[list, add_messages]


def route_tools(state: State) -> Literal[NODE_EXECUTE, NODE_APPROVAL, NODE_RESPOND]:
    """Decides where to go after 'understand'."""
    last_message = state["messages"][-1]

    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return NODE_RESPOND

    tool_name = last_message.tool_calls[0]["name"]

    if tool_name == "config_command":
        return NODE_APPROVAL

    # Safe tools go straight to execution
    return NODE_EXECUTE


def route_approval(state: State) -> Literal[NODE_EXECUTE, NODE_RESPOND]:
    """Decides where to go after 'approval'."""
    last_message = state["messages"][-1]

    if isinstance(last_message, ToolMessage):
        return NODE_RESPOND

    # Approved? Go to execution
    return NODE_EXECUTE


def create_graph():
    workflow = StateGraph(State)

    workflow.add_node(NODE_UNDERSTAND, understand_node)
    workflow.add_node(NODE_APPROVAL, approval_node)
    workflow.add_node(NODE_EXECUTE, execute_node)  # Single node add
    workflow.add_node(NODE_RESPOND, respond_node)

    workflow.set_entry_point(NODE_UNDERSTAND)

    workflow.add_conditional_edges(
        NODE_UNDERSTAND,
        route_tools,
        {
            NODE_EXECUTE: NODE_EXECUTE,
            NODE_APPROVAL: NODE_APPROVAL,
            NODE_RESPOND: NODE_RESPOND,
        },
    )

    workflow.add_conditional_edges(
        NODE_APPROVAL,
        route_approval,
        {NODE_EXECUTE: NODE_EXECUTE, NODE_RESPOND: NODE_RESPOND},
    )

    # Both paths lead here now
    workflow.add_edge(NODE_EXECUTE, NODE_RESPOND)
    workflow.add_edge(NODE_RESPOND, END)

    return workflow.compile(checkpointer=MemorySaver())
