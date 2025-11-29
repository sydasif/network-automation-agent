"""Agent nodes definition for the Network AI Agent."""

import logging
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage, trim_messages
from langchain_core.messages.utils import (
    count_tokens_approximately,
)
from langchain_groq import ChatGroq
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt

from settings import (
    GROQ_API_KEY,
    LLM_MODEL_NAME,
    LLM_TEMPERATURE,
    MAX_HISTORY_TOKENS,
)
from tools.config import config_command
from tools.show import show_command
from utils.devices import get_device_info

logger = logging.getLogger(__name__)

# --- CONSTANTS ---
NODE_UNDERSTAND = "understand"
NODE_APPROVAL = "approval"
NODE_EXECUTE = "execute"
RESUME_APPROVED = "approved"
RESUME_DENIED = "denied"


UNDERSTAND_PROMPT = """
You are a network automation assistant.

Device inventory:
{device_inventory}

Role: Understand user requests and turns into network operations or normal responses (chat).

Tools:
- `show_command`: read-only (show/get/display)
- `config_command`: configuration changes (config/set/delete)

Rules:
- Call tools only for explicit network operations; do not call for greetings or general chat.
- Match syntax to each platform. If a command fails, include the device error. Confirm successful config changes.
- Multi-device: detect target devices, produce device-specific commands per platform (IOS, EOS, JunOS, etc.).

Output:
- Concise, device-tagged results (use markdown for clarity).
- Make a short note of actions taken or errors encountered.
"""


class State(TypedDict):
    messages: Annotated[list, add_messages]


def _create_llm() -> ChatGroq:
    """Create and return a single LLM instance.

    Raises:
        RuntimeError: If GROQ_API_KEY is not set.
    """
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set")

    return ChatGroq(temperature=LLM_TEMPERATURE, model_name=LLM_MODEL_NAME, api_key=GROQ_API_KEY)


llm = _create_llm()
llm_with_tools = llm.bind_tools([show_command, config_command])
execute_node = ToolNode([show_command, config_command])


def understand_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Decide which tool to call.

    ✅ FIXED: Now using proper LangChain trim_messages with count_tokens_approximately
    """
    messages = state.get("messages", [])

    # 1. System Message (Cached by get_device_info)
    inventory_str = get_device_info()
    system_msg = SystemMessage(content=UNDERSTAND_PROMPT.format(device_inventory=inventory_str))

    # 2. ✅ FIXED: Proper LangChain message trimming
    # Using the built-in count_tokens_approximately for fast, accurate token counting
    # This is LangChain's recommended approach for production use
    try:
        trimmed_msgs = trim_messages(
            messages,
            max_tokens=MAX_HISTORY_TOKENS,  # ✅ Realistic token limit (was 10!)
            strategy="last",  # Keep most recent messages
            token_counter=count_tokens_approximately,  # ✅ Fast approximate counter
            start_on="human",  # Ensure valid chat history
            include_system=False,  # System message added separately
            allow_partial=False,  # Keep complete messages only
        )

        # 3. Log context usage for monitoring (optional but recommended)
        if len(messages) > len(trimmed_msgs):
            # Only count tokens if we actually trimmed
            original_tokens = count_tokens_approximately(messages)
            trimmed_tokens = count_tokens_approximately(trimmed_msgs)

            logger.info(
                f"Context trimmed: {len(messages)} messages (~{original_tokens} tokens) "
                f"→ {len(trimmed_msgs)} messages (~{trimmed_tokens} tokens)"
            )

    except Exception as trim_error:
        # Fallback: if trim_messages fails for any reason, keep last 20 messages
        logger.warning(
            f"Message trimming failed: {trim_error}. Using fallback (last 20 messages)."
        )
        trimmed_msgs = messages[-20:] if len(messages) > 20 else messages

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
