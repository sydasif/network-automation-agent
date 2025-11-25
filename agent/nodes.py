"""Agent nodes definition for the Network AI Agent.

This module defines the state, constants, and node logic for the LangGraph workflow.
It includes the understanding node, approval node, and supporting utilities.
"""

import logging
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_groq import ChatGroq
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt

from settings import GROQ_API_KEY, LLM_MODEL_NAME, LLM_TEMPERATURE, MAX_HISTORY_MESSAGES
from tools.config import config_command
from tools.show import show_command
from utils.devices import get_all_device_names

logger = logging.getLogger(__name__)

# --- NODE CONSTANTS ---
NODE_UNDERSTAND = "understand"
NODE_APPROVAL = "approval"
NODE_EXECUTE = "execute"

# --- APPROVAL RESUME CONSTANTS ---
RESUME_APPROVED = "approved"
RESUME_DENIED = "denied"

# --- PROMPTS ---
UNDERSTAND_PROMPT = """
You are a network automation assistant.

**Available Devices:**
{device_names}

**Tools:**
1. `show_command`: For read-only output (show, list, get).
   - Args: `devices` (list of str), `command` (str)
2. `config_command`: For configuration changes (set, create, delete).
   - Args: `devices` (list of str), `configs` (list of str)

**Examples:**
- User: "Show version on sw1"
  Call: show_command(devices=["sw1"], command="show version")

- User: "Create vlan 10 on sw1 and sw2"
  Call: config_command(devices=["sw1", "sw2"], configs=["vlan 10"])

**Guidelines:**
1. Always check 'Available Devices'. Do not use device names that are not listed.
2. If multiple config lines are needed, pass them as a list to `config_command`.
3. If the user intention is unclear, ask for clarification.
"""


# --- STATE DEFINITION ---
class State(TypedDict):
    """Defines the state structure for the LangGraph workflow."""

    messages: Annotated[list, add_messages]


# --- LLM SETUP ---
def _create_llm():
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set in environment")
    return ChatGroq(temperature=LLM_TEMPERATURE, model_name=LLM_MODEL_NAME, api_key=GROQ_API_KEY)


def _limit_history(messages: list) -> list:
    return messages[-MAX_HISTORY_MESSAGES:]


llm = _create_llm()
# Bind tools to the LLM
tools = [show_command, config_command]
llm_with_tools = llm.bind_tools(tools)
execute_node = ToolNode(tools)


# --- NODES ---
def understand_node(state: dict[str, Any]) -> dict[str, Any]:
    """Processes user requests and selects appropriate tools for execution."""
    messages = state.get("messages", [])

    # Load inventory dynamically
    device_names = get_all_device_names()

    # Fallback if inventory is empty
    if not device_names:
        device_names = ["No devices found in inventory"]

    system_msg = SystemMessage(
        content=UNDERSTAND_PROMPT.format(device_names=", ".join(device_names))
    )

    recent_messages = _limit_history(messages)

    try:
        # Invoke LLM
        response = llm_with_tools.invoke([system_msg] + recent_messages)
        return {"messages": [response]}

    except Exception as e:
        error_msg = str(e)
        logger.error(f"LLM Invocation failed: {error_msg}")

        if "429" in error_msg:
            return {
                "messages": [
                    AIMessage(
                        content="⚠️ **Rate Limit Exceeded**: The AI model is currently overloaded. Please wait a moment or switch to a smaller model (e.g., llama-3.1-8b-instant)."
                    )
                ]
            }

        # Generic fallback
        return {
            "messages": [
                AIMessage(
                    content="I encountered an error processing your request. Please try again."
                )
            ]
        }


def approval_node(state: dict[str, Any]) -> dict[str, Any] | None:
    """Handles human approval for configuration changes."""
    last_msg = state["messages"][-1]

    # Check if the last message contains tool calls that require approval
    if not hasattr(last_msg, "tool_calls") or not last_msg.tool_calls:
        return None

    tool_call = last_msg.tool_calls[0]

    # Pause execution to request user approval
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
