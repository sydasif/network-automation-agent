"""Defines the state graph for the network automation agent.

This module creates a LangGraph-based workflow that handles the conversation
flow between understanding user requests, executing network commands, and
responding to the user with formatted results.

The workflow implements a three-node architecture:
- Understand: Parses user intent and determines if tools need to be executed
- Execute: Runs network commands on specified devices
- Respond: Formats and delivers results to the user

The state management uses LangGraph's built-in checkpointing to maintain
conversation history across interactions.
"""

from typing import Annotated, Any, Literal, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from graph.nodes import execute_node, respond_node, understand_node


class State(TypedDict):
    """Defines the state structure for the LangGraph workflow.

    This state maintains the conversation context and execution results
    throughout the workflow lifecycle.

    Attributes:
        messages: List of conversation messages between user and agent
        results: Dictionary to store execution results and metadata
    """

    messages: Annotated[list, add_messages]
    results: dict[str, Any]


def should_execute(state: State) -> Literal["execute", "respond"]:
    """Determines the next step in the workflow based on tool calls.

    Inspects the last message to see if it contains tool calls that need
    to be executed. If tool calls are present, routes to the 'execute' node.
    Otherwise, proceeds directly to the 'respond' node.

    Args:
        state: The current state containing conversation messages.

    Returns:
        Literal string indicating whether to 'execute' tools or 'respond' directly.
    """
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "execute"
    return "respond"


def create_graph():
    """Creates and configures the LangGraph workflow for the network agent.

    Sets up the three-node state machine with appropriate routing logic.
    The workflow begins at the 'understand' node where user input is processed,
    then conditionally routes to 'execute' if commands need to be run on devices,
    and finally to 'respond' to format and return the results to the user.

    The workflow includes memory checkpointing to maintain conversation history.

    Returns:
        A compiled LangGraph workflow instance ready to process conversations.
    """
    workflow = StateGraph(State)

    workflow.add_node("understand", understand_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("respond", respond_node)

    workflow.set_entry_point("understand")
    workflow.add_conditional_edges(
        "understand",
        should_execute,
        {"execute": "execute", "respond": "respond"},
    )
    workflow.add_edge("execute", "respond")
    workflow.add_edge("respond", END)

    return workflow.compile(checkpointer=MemorySaver())
