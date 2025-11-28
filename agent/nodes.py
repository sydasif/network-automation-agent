"""Agent nodes definition for the Network AI Agent."""

import logging
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage, trim_messages
from langchain_core.messages.utils import (
    count_tokens_approximately,
)  # ✅ Built-in fast token counter
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
RESUME_DENIED = "denied"

# ✅ FIXED: Proper token-based limits using LangChain recommendations
MAX_CONTEXT_TOKENS = 4000  # Conservative limit for most models
# Reserve ~500 tokens for system prompt + response buffer
MAX_HISTORY_TOKENS = 3500

UNDERSTAND_PROMPT = """
You are a network engineer assistant.

**Network Inventory:**
{device_inventory}

**Your Role:**
Analyze user requests and execute the appropriate network commands using the correct tools and platform-specific command syntax.

**Tool Selection:**
- Use 'show_command' for retrieving information (e.g. show version, show interfaces)
- Use 'config_command' for making configuration changes (e.g. vlan creation, interface configuration)

**Critical Requirements:**
1. Match commands to the device's specific platform (Cisco IOS, Arista EOS, Juniper JunOS, etc.)
2. Avoid unnecessary commands; only execute what is required to fulfill the request
3. If the request is ambiguous about which device or unclear about intent, ask for clarification

**Context Awareness:**
Different network platforms use different command structures. A command valid for Cisco IOS may not work on Arista EOS.
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
