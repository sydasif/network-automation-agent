"""Defines the state graph for the network automation agent.

This module creates a LangGraph-based workflow that handles the conversation
flow between understanding user requests, executing network commands, and
responding to the user with formatted results.
"""

from typing import Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from graph.nodes import execute_node, respond_node, understand_node


class State(TypedDict):
    """Defines the state structure for the LangGraph workflow.

    Attributes:
        messages: List of conversation messages between user and agent
        results: Dictionary to store execution results and metadata
    """

    messages: list[BaseMessage]
    results: dict[str, Any]


def create_graph():
    """Creates and configures the LangGraph workflow for the network agent.

    The workflow consists of three main nodes:
    1. 'understand' - Parses user input and determines if tools need to be executed
    2. 'execute' - Runs network commands on the specified devices
    3. 'respond' - Formats and returns results to the user

    The workflow starts at the 'understand' node and conditionally routes
    to either 'execute' (if tools need to be executed) or 'respond'.

    Returns:
        A compiled LangGraph workflow instance ready to process conversations.
    """
    workflow = StateGraph(State)

    workflow.add_node("understand", understand_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("respond", respond_node)

    workflow.set_entry_point("understand")
    # Conditional edge from 'understand' node: route to 'execute' if LLM
    # generated tool calls, else route directly to 'respond'
    workflow.add_conditional_edges(
        "understand",
        lambda s: "execute"
        if hasattr(s["messages"][-1], "tool_calls") and s["messages"][-1].tool_calls
        else "respond",
        {"execute": "execute", "respond": END},
    )
    workflow.add_edge("execute", "respond")
    workflow.add_edge("respond", END)

    return workflow.compile(
        checkpointer=MemorySaver()
    )
