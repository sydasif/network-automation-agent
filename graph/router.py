from typing import Annotated, Literal, TypedDict

from langchain_core.messages import ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

# NEW IMPORT
from graph.consts import (
    NODE_APPROVAL,
    NODE_EXECUTE_READ,
    NODE_EXECUTE_WRITE,
    NODE_RESPOND,
    NODE_UNDERSTAND,
)
from graph.nodes import (
    approval_node,
    read_tool_node,
    respond_node,
    understand_node,
    write_tool_node,
)


class State(TypedDict):
    messages: Annotated[list, add_messages]


def route_tools(state: State) -> Literal[NODE_EXECUTE_READ, NODE_APPROVAL, NODE_RESPOND]:
    """Decides where to go after 'understand'."""
    last_message = state["messages"][-1]

    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return NODE_RESPOND

    tool_name = last_message.tool_calls[0]["name"]

    if tool_name == "config_command":
        return NODE_APPROVAL

    return NODE_EXECUTE_READ


def route_approval(state: State) -> Literal[NODE_EXECUTE_WRITE, NODE_RESPOND]:
    """Decides where to go after 'approval'."""
    last_message = state["messages"][-1]

    # If the approval node inserted a ToolMessage (denial), go to respond
    if isinstance(last_message, ToolMessage):
        return NODE_RESPOND

    return NODE_EXECUTE_WRITE


def create_graph():
    workflow = StateGraph(State)

    workflow.add_node(NODE_UNDERSTAND, understand_node)
    workflow.add_node(NODE_APPROVAL, approval_node)
    workflow.add_node(NODE_EXECUTE_READ, read_tool_node)
    workflow.add_node(NODE_EXECUTE_WRITE, write_tool_node)
    workflow.add_node(NODE_RESPOND, respond_node)

    workflow.set_entry_point(NODE_UNDERSTAND)

    workflow.add_conditional_edges(
        NODE_UNDERSTAND,
        route_tools,
        {
            NODE_EXECUTE_READ: NODE_EXECUTE_READ,
            NODE_APPROVAL: NODE_APPROVAL,
            NODE_RESPOND: NODE_RESPOND,
        },
    )

    workflow.add_conditional_edges(
        NODE_APPROVAL,
        route_approval,
        {NODE_EXECUTE_WRITE: NODE_EXECUTE_WRITE, NODE_RESPOND: NODE_RESPOND},
    )

    workflow.add_edge(NODE_EXECUTE_READ, NODE_RESPOND)
    workflow.add_edge(NODE_EXECUTE_WRITE, NODE_RESPOND)
    workflow.add_edge(NODE_RESPOND, END)

    return workflow.compile(checkpointer=MemorySaver())
