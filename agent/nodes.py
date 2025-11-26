"""Agent nodes definition for the Network AI Agent."""

import logging
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_groq import ChatGroq
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt

from settings import GROQ_API_KEY, LLM_MODEL_NAME, LLM_TEMPERATURE, MAX_HISTORY_MESSAGES

# Import the UPDATED tools (which now have Pydantic schemas)
from tools.config import config_command
from tools.show import show_command
from utils.devices import get_device_info

logger = logging.getLogger(__name__)

# --- NODE CONSTANTS ---
NODE_UNDERSTAND = "understand"
NODE_APPROVAL = "approval"
NODE_EXECUTE = "execute"
RESUME_APPROVED = "approved"
RESUME_DENIED = "denied"

# --- PROMPT ---
# Updated to include platform information for better command generation
UNDERSTAND_PROMPT = """
You are a network automation assistant.

**Network Inventory (Name & Platform):**
{device_inventory}

**Instructions:**
1. Look at the 'Platform' in the inventory above.
2. Ensure the commands you generate are valid for that specific platform
   (e.g., do not use 'write mem' on Juniper).
3. Use 'show_command' for reading data.
4. Use 'config_command' for changing settings.
"""


# --- STATE ---
class State(TypedDict):
    """State structure for the LangGraph workflow."""

    messages: Annotated[list, add_messages]


# --- LLM & TOOLS ---
def _create_llm() -> ChatGroq:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set")
    return ChatGroq(temperature=LLM_TEMPERATURE, model_name=LLM_MODEL_NAME, api_key=GROQ_API_KEY)


llm = _create_llm()

# THIS IS THE MAGIC PART:
# By binding these tools, the Pydantic schemas are automatically sent to the LLM.
# The LLM now knows exactly what pattern to use.
tools = [show_command, config_command]
llm_with_tools = llm.bind_tools(tools)

execute_node = ToolNode(tools)


# --- NODES ---
def understand_node(state: dict[str, Any]) -> dict[str, Any]:
    """Decide which tool to call."""
    messages = state.get("messages", [])

    # FETCH THE SMART DATA (includes platform info)
    inventory_str = get_device_info()

    if not inventory_str:
        inventory_str = "No devices found."

    # INJECT IT INTO THE BRAIN
    system_msg = SystemMessage(content=UNDERSTAND_PROMPT.format(device_inventory=inventory_str))

    # Keep context short
    recent_messages = messages[-MAX_HISTORY_MESSAGES:]

    try:
        # The LLM will now generate the correct pattern automatically
        response = llm_with_tools.invoke([system_msg] + recent_messages)
        return {"messages": [response]}

    except Exception as e:
        logger.error("LLM Error: %s", e)
        # Graceful error handling
        if "429" in str(e):
            msg = "⚠️ Rate limit reached. Please wait or switch models."
        else:
            msg = "I encountered an error. Please try again."

        return {"messages": [AIMessage(content=msg)]}


def approval_node(state: dict[str, Any]) -> dict[str, Any] | None:
    """Ask for permission."""
    last_msg = state["messages"][-1]

    if not hasattr(last_msg, "tool_calls") or not last_msg.tool_calls:
        return None

    tool_call = last_msg.tool_calls[0]

    # Interrupt execution to ask the user
    decision = interrupt({"type": "approval_request", "tool_call": tool_call})

    if decision == RESUME_APPROVED:
        return None

    return {
        "messages": [
            ToolMessage(
                tool_call_id=tool_call["id"],
                content=f"❌ User denied permission: {tool_call['name']}",
            )
        ],
    }
