from typing import TypedDict

from langgraph.graph import END, StateGraph

from graph.nodes import execute_node, respond_node, understand_node


class State(TypedDict):
    messages: list
    results: dict


def create_graph():
    workflow = StateGraph(State)

    workflow.add_node("understand", understand_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("respond", respond_node)

    workflow.set_entry_point("understand")
    workflow.add_conditional_edges(
        "understand",
        lambda s: "execute"
        if hasattr(s["messages"][-1], "tool_calls") and s["messages"][-1].tool_calls
        else "respond",
        {"execute": "execute", "respond": END},
    )
    workflow.add_edge("execute", "respond")
    workflow.add_edge("respond", END)

    return workflow.compile()
