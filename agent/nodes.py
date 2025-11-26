"""Agent nodes definition for the Network AI Agent."""

import logging
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage, trim_messages
from langchain_core.runnables import RunnableWithFallbacks
from langchain_groq import ChatGroq
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt

from settings import GROQ_API_KEY, LLM_FALLBACK_MODELS, LLM_MODEL_NAME, LLM_TEMPERATURE
from tools.config import config_command
from tools.show import show_command
from utils.devices import get_device_info

logger = logging.getLogger(__name__)

# --- CONSTANTS ---
NODE_UNDERSTAND = "understand"
NODE_APPROVAL = "approval"
NODE_EXECUTE = "execute"
RESUME_APPROVED = "approved"
RESUME_DENIED = "denied"  # <--- Added back

UNDERSTAND_PROMPT = """
You are a network automation assistant.

**Network Inventory (Name & Platform):**
{device_inventory}

**Instructions:**
1. Look at the 'Platform' in the inventory above.
2. Ensure the commands you generate are valid for that specific platform.
3. Use 'show_command' for reading data.
4. Use 'config_command' for changing settings.
"""


class State(TypedDict):
    messages: Annotated[list, add_messages]


def _create_llm() -> RunnableWithFallbacks:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set")

    primary = ChatGroq(
        temperature=LLM_TEMPERATURE, model_name=LLM_MODEL_NAME, api_key=GROQ_API_KEY
    )
    fallbacks = [
        ChatGroq(temperature=LLM_TEMPERATURE, model_name=m, api_key=GROQ_API_KEY)
        for m in LLM_FALLBACK_MODELS
    ]
    return primary.with_fallbacks(fallbacks=fallbacks)


llm = _create_llm()
# Bind tools: flexible pydantic models are converted to JSON schema here
llm_with_tools = llm.bind_tools([show_command, config_command])
execute_node = ToolNode([show_command, config_command])


def understand_node(state: dict[str, Any]) -> dict[str, Any]:
    """Decide which tool to call."""
    messages = state.get("messages", [])

    # 1. System Message (Cached by get_device_info)
    inventory_str = get_device_info()
    system_msg = SystemMessage(content=UNDERSTAND_PROMPT.format(device_inventory=inventory_str))

    # 2. Context Management
    trimmed_msgs = trim_messages(
        messages,
        strategy="last",
        token_counter=len,
        max_tokens=10,
        start_on="human",
        include_system=False,
    )

    try:
        response = llm_with_tools.invoke([system_msg] + trimmed_msgs)
        return {"messages": [response]}

    except Exception as e:
        logger.error("LLM Error: %s", e)
        err_str = str(e)
        if "429" in err_str:
            msg = "⚠️ Rate limit reached (Groq). Please wait a moment."
        elif "401" in err_str:
            msg = "⚠️ Authentication failed. Check GROQ_API_KEY."
        else:
            msg = "⚠️ An internal error occurred processing your request."

        return {"messages": [AIMessage(content=msg)]}


def approval_node(state: dict[str, Any]) -> dict[str, Any] | None:
    """Ask for permission."""
    last_msg = state["messages"][-1]

    # Safety check: ensure tool_calls exist
    if not hasattr(last_msg, "tool_calls") or not last_msg.tool_calls:
        return None

    tool_call = last_msg.tool_calls[0]

    # Native Interrupt
    decision = interrupt({"type": "approval_request", "tool_call": tool_call})

    if decision == RESUME_APPROVED:
        return None

    # Inject denial message
    return {
        "messages": [
            ToolMessage(
                tool_call_id=tool_call["id"],
                content=f"❌ User denied permission: {tool_call['name']}",
            )
        ],
    }
