from typing import Any

from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt

from graph.consts import RESUME_APPROVED
from graph.prompts import RESPOND_PROMPT, UNDERSTAND_PROMPT
from llm.client import create_llm
from llm.utils import manage_chat_history  # <--- NEW IMPORT
from tools.commands import config_command, show_command
from utils.devices import get_all_device_names

llm = create_llm()
llm_with_tools = llm.bind_tools([show_command, config_command])

read_tool_node = ToolNode([show_command])
write_tool_node = ToolNode([config_command])


def understand_node(state: dict[str, Any]) -> dict[str, Any]:
    """Analyzes user intent and generates tool calls."""
    messages = state.get("messages", [])

    # DRY: Use centralized context manager
    trimmed_messages = manage_chat_history(messages)

    device_names = get_all_device_names()

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

    if not hasattr(last_msg, "tool_calls") or not last_msg.tool_calls:
        return None

    tool_call = last_msg.tool_calls[0]

    decision = interrupt({"type": "approval_request", "tool_call": tool_call})

    if decision == RESUME_APPROVED:
        return None

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
