"""agent/workflow.py: Assembles the LangGraph workflow."""

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
    workflow = StateGraph(State)
    workflow.add_node(NODE_UNDERSTAND, understand_node)
    workflow.add_node(NODE_APPROVAL, approval_node)
    workflow.add_node(NODE_EXECUTE, execute_node)

    workflow.set_entry_point(NODE_UNDERSTAND)

    workflow.add_conditional_edges(
        NODE_UNDERSTAND,
        route_tools,
        {NODE_EXECUTE: NODE_EXECUTE, NODE_APPROVAL: NODE_APPROVAL, END: END},
    )
    workflow.add_conditional_edges(
        NODE_APPROVAL,
        route_approval,
        {NODE_EXECUTE: NODE_EXECUTE, NODE_UNDERSTAND: NODE_UNDERSTAND},
    )

    # LOOP: Execution output goes back to Understand to be formatted
    workflow.add_edge(NODE_EXECUTE, NODE_UNDERSTAND)

    return workflow.compile(checkpointer=MemorySaver())


# --- HELPER ---
def get_approval_request(snapshot: StateSnapshot) -> dict | None:
    if not snapshot.tasks or not snapshot.tasks[0].interrupts:
        return None
    return snapshot.tasks[0].interrupts[0].value.get("tool_call")
