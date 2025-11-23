"""Defines the state graph and routing logic."""

from typing import Annotated, Any, Literal, TypedDict
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from graph.nodes import understand_node, execute_read_node, execute_write_node, respond_node


class State(TypedDict):
    """Represents the state of the LangGraph workflow.

    Attributes:
        messages: List of conversation messages between user and agent.
        results: Dictionary containing execution results from tool calls.
    """
    messages: Annotated[list, add_messages]
    results: dict[str, Any]


def route_tools(state: State) -> Literal["execute_read", "execute_write", "respond"]:
    """Determines the next node in the workflow based on the tool calls.

    This function inspects the last message in the state to determine if
    any tools were called and routes to the appropriate node based on the
    tool type.

    Args:
        state: Current state of the workflow containing messages and results.

    Returns:
        Literal indicating the next node to execute:
        - "execute_read": For read-only commands (show_command)
        - "execute_write": For configuration commands (config_command)
        - "respond": When no tools were called, directly respond to the user
    """
    last_message = state["messages"][-1]
    # Check if the last message has tool calls, if not, respond directly
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return "respond"

    # Get the name of the first tool called to determine routing
    tool_name = last_message.tool_calls[0]["name"]
    # Route to execute_write for config_command, execute_read for others
    return "execute_write" if tool_name == "config_command" else "execute_read"


def create_graph():
    """Creates and compiles the LangGraph workflow for the network agent.

    This function defines the state graph with nodes for understanding user
    intent, executing read/write commands, and responding to the user. It
    sets up conditional routing based on tool calls and includes a memory
    saver for state persistence.

    Returns:
        Compiled LangGraph workflow instance ready for use.
    """
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
