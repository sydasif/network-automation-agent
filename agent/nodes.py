"""agent/nodes.py: Defines the graph state, constants, and node logic."""

from typing import Annotated, Any, TypedDict

from langchain_core.messages import SystemMessage, ToolMessage
from langchain_groq import ChatGroq
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt

from settings import GROQ_API_KEY, LLM_MODEL_NAME, LLM_TEMPERATURE, MAX_HISTORY_MESSAGES
from tools.commands import config_command, show_command
from utils.devices import get_all_device_names

# --- CONSTANTS ---
NODE_UNDERSTAND = "understand"
NODE_APPROVAL = "approval"
NODE_EXECUTE = "execute"

RESUME_APPROVED = "approved"
RESUME_DENIED = "denied"

# --- PROMPTS ---
UNDERSTAND_PROMPT = """
You are a network automation assistant.

You have access to two tools:
1. show_command: For retrieving information (Read-Only).
2. config_command: For applying changes (Read-Write).

Rules:
- Always check device TYPES before issuing commands.
- If the user asks to CHANGE configuration (create, delete, set, update config), use 'config_command'.
- If the user asks to SHOW information, use 'show_command'.
- When receiving tool output, format it as a clean Markdown summary (use tables for lists).
- Do not output raw JSON.

Available devices: {device_names}
"""


# --- STATE DEFINITION ---
class State(TypedDict):
    messages: Annotated[list, add_messages]


# --- LLM SETUP ---
def _create_llm():
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set in environment")
    return ChatGroq(temperature=LLM_TEMPERATURE, model_name=LLM_MODEL_NAME, api_key=GROQ_API_KEY)


def _limit_history(messages: list) -> list:
    """KISS: Keep only the last N messages."""
    return messages[-MAX_HISTORY_MESSAGES:]


llm = _create_llm()
tools = [show_command, config_command]
llm_with_tools = llm.bind_tools(tools)
execute_node = ToolNode(tools)


# --- NODES ---
def understand_node(state: dict[str, Any]) -> dict[str, Any]:
    messages = state.get("messages", [])

    # Simple list slicing
    recent_messages = _limit_history(messages)

    device_names = get_all_device_names()
    system_msg = SystemMessage(
        content=UNDERSTAND_PROMPT.format(device_names=", ".join(device_names))
    )

    response = llm_with_tools.invoke([system_msg] + recent_messages)
    return {"messages": [response]}


def approval_node(state: dict[str, Any]) -> dict[str, Any] | None:
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
