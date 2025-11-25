"""Agent nodes definition for the Network AI Agent.

This module defines the state, constants, and node logic for the LangGraph workflow.
It includes the understanding node, approval node, and supporting utilities.
"""

from typing import Annotated, Any, TypedDict

from langchain_core.messages import SystemMessage, ToolMessage
from langchain_groq import ChatGroq
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt

from settings import GROQ_API_KEY, LLM_MODEL_NAME, LLM_TEMPERATURE, MAX_HISTORY_MESSAGES
from tools.config import config_command
from tools.show import show_command
from utils.devices import get_all_device_names

# --- NODE CONSTANTS ---
# These constants represent the different nodes in the workflow graph
NODE_UNDERSTAND = "understand"  # LLM node that understands user requests and selects tools
NODE_APPROVAL = "approval"  # Human approval node for sensitive operations
NODE_EXECUTE = "execute"  # Tool execution node that runs selected tools on devices

# --- APPROVAL RESUME CONSTANTS ---
# These constants represent the values returned when resuming from approval interruption
RESUME_APPROVED = "approved"  # Value returned when user approves an action
RESUME_DENIED = "denied"  # Value returned when user denies an action

# --- PROMPTS ---
UNDERSTAND_PROMPT = """
You are a network automation assistant.

You have access to two tools:
1. show_command: For retrieving information (Read-Only).
2. config_command: For applying changes (Read-Write).

GUIDELINES:
- **Batching**: You can target multiple devices at once by passing a list of names to the tools.
- **Safety**: Always check device TYPES before issuing complex configs.
- **Output**: Format output as a clean Markdown summary (use tables for lists).

Available devices: {device_names}
"""


# --- STATE DEFINITION ---
class State(TypedDict):
    """Defines the state structure for the LangGraph workflow.

    Attributes:
        messages: A list of messages in the conversation history.
    """

    messages: Annotated[list, add_messages]


# --- LLM SETUP ---
def _create_llm():
    """Creates and configures the LLM instance for the agent.

    Returns:
        A configured ChatGroq instance.

    Raises:
        RuntimeError: If the GROQ_API_KEY is not set in the environment.
    """
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set in environment")
    return ChatGroq(temperature=LLM_TEMPERATURE, model_name=LLM_MODEL_NAME, api_key=GROQ_API_KEY)


def _limit_history(messages: list) -> list:
    """Keep only the last N messages in the conversation history.

    Args:
        messages: A list of messages in the conversation history.

    Returns:
        A list containing the most recent messages up to MAX_HISTORY_MESSAGES.
    """
    return messages[-MAX_HISTORY_MESSAGES:]


llm = _create_llm()
tools = [show_command, config_command]
llm_with_tools = llm.bind_tools(tools)
execute_node = ToolNode(tools)


# --- NODES ---
def understand_node(state: dict[str, Any]) -> dict[str, Any]:
    """Processes user requests and selects appropriate tools for execution.

    This node acts as the main LLM-driven component that understands user requests
    and decides which tools to call based on the request and available devices.

    Args:
        state: The current state of the workflow containing messages.

    Returns:
        A dictionary containing the updated messages with the LLM response.
    """
    messages = state.get("messages", [])

    # Load inventory dynamically to get current device list
    device_names = get_all_device_names()

    system_msg = SystemMessage(
        content=UNDERSTAND_PROMPT.format(device_names=", ".join(device_names))
    )

    # Prepend system message + limited history to maintain context
    recent_messages = _limit_history(messages)

    # Invoke LLM with system message and recent conversation history
    response = llm_with_tools.invoke([system_msg] + recent_messages)
    return {"messages": [response]}


def approval_node(state: dict[str, Any]) -> dict[str, Any] | None:
    """Handles human approval for configuration changes.

    This node intercepts configuration commands and requests human approval
    before they are executed on network devices. If denied, it returns
    an appropriate message explaining the denial.

    Args:
        state: The current state of the workflow containing messages.

    Returns:
        None if approved, or a dictionary containing a denial message if denied.
    """
    last_msg = state["messages"][-1]
    # Check if the last message contains tool calls that require approval
    if not hasattr(last_msg, "tool_calls") or not last_msg.tool_calls:
        return None

    tool_call = last_msg.tool_calls[0]

    # Pause execution to request user approval, blocking until a decision is made
    decision = interrupt({"type": "approval_request", "tool_call": tool_call})

    # If user approved, continue with no additional messages
    if decision == RESUME_APPROVED:
        return None

    # If user denied, return a message explaining the denial
    return {
        "messages": [
            ToolMessage(
                tool_call_id=tool_call["id"],
                content=f"❌ User denied permission to execute: {tool_call['name']}",
            )
        ]
    }
