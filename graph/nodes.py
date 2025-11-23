from typing import Any
from langchain_core.messages import SystemMessage, ToolMessage, trim_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt

from graph.prompts import RESPOND_PROMPT, UNDERSTAND_PROMPT
from llm.client import create_llm
from tools.commands import show_command, config_command
from utils.database import get_db
from utils.devices import get_all_device_names

llm = create_llm()
# Bind tools so the LLM knows they exist
llm_with_tools = llm.bind_tools([show_command, config_command])

# --- 1. Define Native Tool Nodes ---
# These replace your custom execute functions.
# ToolNode automatically handles parsing, execution, and error catching.
read_tool_node = ToolNode([show_command])
write_tool_node = ToolNode([config_command])


def understand_node(state: dict[str, Any]) -> dict[str, Any]:
    """Analyzes user intent and generates tool calls."""
    messages = state.get("messages", [])

    # Keep context manageable
    trimmed_messages = trim_messages(
        messages,
        max_tokens=2000,
        strategy="last",
        token_counter=len,
        start_on="human",
        end_on=("human", "ai"),
        include_system=False,
    )

    with get_db() as db:
        device_names = get_all_device_names(db)

    system_msg = SystemMessage(
        content=UNDERSTAND_PROMPT.format(device_names=", ".join(device_names))
    )

    response = llm_with_tools.invoke([system_msg] + trimmed_messages)
    return {"messages": [response]}


def approval_node(state: dict[str, Any]) -> dict[str, Any] | None:
    """
    Gatekeeper node.
    - Pauses execution for human review.
    - If Approved: Returns None (Graph continues to write_tool_node).
    - If Denied: Returns a ToolMessage (Graph skips execution and goes to Respond).
    """
    last_msg = state["messages"][-1]

    # Safety check: Ensure there is actually a tool call
    if not hasattr(last_msg, "tool_calls") or not last_msg.tool_calls:
        return None

    # We only interrupt for the first tool call (simplification)
    tool_call = last_msg.tool_calls[0]

    # --- NATIVE INTERRUPT ---
    # This pauses the graph. The value returned here is what you pass
    # to Command(resume="value") in main.py
    decision = interrupt({"type": "approval_request", "tool_call": tool_call})

    if decision == "approved":
        # Return None so the state remains unchanged.
        # The next node (write_tool_node) will see the original tool call and execute it.
        return None

    # If denied, we manually inject a "ToolMessage" representing the denial.
    # This satisfies the LLM's expectation that a tool was "run".
    return {
        "messages": [
            ToolMessage(
                tool_call_id=tool_call["id"],
                content=f"❌ User denied permission to execute: {tool_call['name']}",
            )
        ]
    }


def respond_node(state: dict[str, Any]) -> dict[str, Any]:
    """Synthesizes the final response."""
    messages = state["messages"]
    synthesis_prompt = SystemMessage(content=RESPOND_PROMPT)
    response = llm.invoke(messages + [synthesis_prompt])
    return {"messages": [response]}
