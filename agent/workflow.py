"""LangGraph workflow assembly for the Network AI Agent.

This module defines and assembles the complete LangGraph workflow that
processes user requests through understanding, approval, and execution phases.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import StateSnapshot

from agent.nodes import (
    NODE_APPROVAL,
    NODE_EXECUTE,
    NODE_UNDERSTAND,
    State,
    approval_node,
    execute_node,
    understand_node,
)
from agent.router import route_approval, route_tools


def create_graph():
    """Creates and compiles the LangGraph workflow for the network agent.

    The workflow contains three main nodes:
    - NODE_UNDERSTAND: Processes user requests and selects appropriate tools
    - NODE_APPROVAL: Handles human approval for configuration changes
    - NODE_EXECUTE: Executes the selected tools on network devices

    The workflow is set up with conditional routing between nodes based on
    whether configuration changes are requested.

    Returns:
        A compiled LangGraph workflow ready to process requests.
    """
    # Create the state graph with the defined state structure
    workflow = StateGraph(State)
    # Add the three main nodes to the workflow
    workflow.add_node(NODE_UNDERSTAND, understand_node)
    workflow.add_node(NODE_APPROVAL, approval_node)
    workflow.add_node(NODE_EXECUTE, execute_node)

    # Set the starting node for the workflow
    workflow.set_entry_point(NODE_UNDERSTAND)

    # Add conditional routing from Understand node based on the tool called
    workflow.add_conditional_edges(
        NODE_UNDERSTAND,
        route_tools,
        {NODE_EXECUTE: NODE_EXECUTE, NODE_APPROVAL: NODE_APPROVAL, END: END},
    )
    # Add conditional routing from Approval node based on user decision
    workflow.add_conditional_edges(
        NODE_APPROVAL,
        route_approval,
        {NODE_EXECUTE: NODE_EXECUTE, NODE_UNDERSTAND: NODE_UNDERSTAND},
    )

    # LOOP: Execution output goes back to Understand to be formatted for user response
    workflow.add_edge(NODE_EXECUTE, NODE_UNDERSTAND)

    # Compile the workflow with a memory saver for state persistence
    return workflow.compile(checkpointer=MemorySaver())


# --- HELPER ---
def get_approval_request(snapshot: StateSnapshot) -> dict | None:
    """Extracts the approval request from a workflow state snapshot.

    This helper function checks if there's an active approval request
    in the workflow state and returns the tool call information if present.

    Args:
        snapshot: The current state snapshot of the workflow.

    Returns:
        A dictionary containing the tool call information if there's an
        active approval request, otherwise None.
    """
    # Check if there are active tasks and interrupts in the snapshot
    if not snapshot.tasks or not snapshot.tasks[0].interrupts:
        return None
    # Return the tool call information from the interrupt
    return snapshot.tasks[0].interrupts[0].value.get("tool_call")
