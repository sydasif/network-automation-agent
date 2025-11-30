"""Agent nodes definition for the Network AI Agent."""

import logging
from functools import lru_cache
from typing import Annotated, Any, TypedDict

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    trim_messages,
)
from langchain_core.messages.utils import (
    count_tokens_approximately,
)
from langchain_groq import ChatGroq
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from settings import (
    GROQ_API_KEY,
    LLM_MODEL_NAME,
    LLM_TEMPERATURE,
    MAX_HISTORY_TOKENS,
)
from tools.config import config_command
from tools.plan import plan_task
from tools.response import respond
from tools.show import show_command
from utils.devices import get_device_info

logger = logging.getLogger(__name__)

# --- CONSTANTS ---
NODE_UNDERSTAND = "understand"
NODE_PLANNER = "planner"
NODE_APPROVAL = "approval"
NODE_EXECUTE = "execute"
RESUME_APPROVED = "approved"
RESUME_DENIED = "denied"


UNDERSTAND_PROMPT = """
You are a network automation assistant.

Device inventory:
{device_inventory}

Role: Understand user requests and translate them into network operations or provide normal chat responses.

Tools:
- `show_command`: read-only (show/get/display)
- `config_command`: configuration changes (config/set/delete)
- `respond`: Final response to the user. Call this ONLY when all tasks are done.

Rules:
- Call tools only for explicit network operations; do not call for greetings or general chat.
- Match syntax to each platform. If a command fails, include the device error. Confirm successful config changes.
- Multi-device: detect target devices, produce device-specific commands per platform (IOS, EOS, JunOS, etc.).
"""


STRUCTURED_OUTPUT_PROMPT = """
You are a network automation assistant.

Your task is to analyze the provided network command output and structure it.
Do NOT call any more tools.
Analyze the output from the executed tool and return a structured JSON response.

You MUST return a JSON object with exactly these keys:
- "summary": A human-readable executive summary. Highlight operational status, health, and anomalies. Use Markdown for readability.
- "structured_data": The parsed data as a list or dictionary.
- "errors": A list of error strings (or null if none).

Example:
{
  "summary": "Interface Eth1 is up.",
  "structured_data": {"interfaces": [{"name": "Eth1", "status": "up"}]},
  "errors": []
}
"""


class NetworkResponse(BaseModel):
    """Structured response for network operations."""

    summary: str = Field(
        description="A human-readable summary highlighting operational status and anomalies."
    )
    structured_data: dict | list = Field(
        description="The parsed data from the device output in JSON format (list or dict)."
    )
    errors: list[str] | None = Field(
        description="List of any errors encountered during execution."
    )


PLANNER_PROMPT = """
You are a network automation planner.
Your job is to break down complex user requests into a series of logical steps.

User Request: {user_request}

Return a list of steps to accomplish this task.
Each step should be a clear, actionable description.
Do not generate code or commands yet, just the plan.
"""

SUMMARY_PROMPT = """
Distill the following conversation history into a concise summary.
Include key details like device names, specific issues mentioned, and actions taken.
Do not lose important context needed for future turns.
"""


def summarize_messages(messages: list) -> str:
    """Summarize a list of messages using the LLM."""
    llm = get_llm()
    prompt = f"{SUMMARY_PROMPT}\n\nMessages:\n"
    for msg in messages:
        role = "User" if isinstance(msg, HumanMessage) else "Assistant"
        prompt += f"{role}: {msg.content}\n"

    response = llm.invoke(prompt)
    return response.content


class Plan(BaseModel):
    """A list of steps to complete a task."""

    steps: list[str] = Field(description="List of steps to execute.")


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


# Lazy-loading LLM instances using lru_cache for singleton pattern
# This prevents import-time crashes and improves testability


@lru_cache(maxsize=1)
def get_llm() -> ChatGroq:
    """Get or create the LLM instance (lazy-loaded singleton)."""
    return _create_llm()


@lru_cache(maxsize=1)
def get_llm_with_tools():
    """Get or create the LLM instance with tools bound (lazy-loaded singleton)."""
    return get_llm().bind_tools([show_command, config_command, plan_task, respond])


# ToolNode is stateless and can be created at module level
execute_node = ToolNode([show_command, config_command, plan_task])


def understand_node(state: dict[str, Any]) -> dict[str, Any]:
    """Process user messages and decide which tool to call or structure tool outputs.

    This node handles two scenarios:
    1. User input: Routes to appropriate tools (show_command or config_command).
    2. Tool output: Structures the response using LLM for human-readable display.

    Args:
        state: Current graph state containing message history

    Returns:
        Updated state with LLM response
    """
    messages = state.get("messages", [])

    # Message trimming for context window management
    # Using the built-in count_tokens_approximately for fast token counting
    try:
        trimmed_msgs = trim_messages(
            messages,
            max_tokens=MAX_HISTORY_TOKENS,
            strategy="last",
            token_counter=count_tokens_approximately,
            start_on="human",
            include_system=False,
            allow_partial=False,
        )

        # Log context usage for monitoring
        if len(messages) > len(trimmed_msgs):
            # Only count tokens if we actually trimmed
            original_tokens = count_tokens_approximately(messages)
            trimmed_tokens = count_tokens_approximately(trimmed_msgs)

            logger.info(
                f"Context trimmed: {len(messages)} messages (~{original_tokens} tokens) "
                f"→ {len(trimmed_msgs)} messages (~{trimmed_tokens} tokens)"
            )

            # Summarize the dropped messages
            dropped_count = len(messages) - len(trimmed_msgs)
            if dropped_count > 0:
                dropped_msgs = messages[:dropped_count]
                summary = summarize_messages(dropped_msgs)

                # Create a summary message and prepend it to trimmed_msgs
                summary_msg = SystemMessage(content=f"Previous Conversation Summary:\n{summary}")
                trimmed_msgs = [summary_msg] + trimmed_msgs
                logger.info("Added conversation summary for dropped messages.")

    except (ValueError, IndexError, NotImplementedError) as trim_error:
        # Catch specific exceptions that trim_messages can raise
        logger.warning(
            f"Message trimming failed ({type(trim_error).__name__}): {trim_error}. "
            "Using fallback strategy."
        )
        # Fallback: Use a simple strategy to keep recent messages
        # Start with last 10 messages and verify they fit within token limit
        fallback_count = min(10, len(messages))
        trimmed_msgs = messages[-fallback_count:] if messages else []

        # Verify fallback doesn't exceed token limit
        if trimmed_msgs:
            fallback_tokens = count_tokens_approximately(trimmed_msgs)
            while fallback_tokens > MAX_HISTORY_TOKENS and fallback_count > 1:
                fallback_count -= 1
                trimmed_msgs = messages[-fallback_count:]
                fallback_tokens = count_tokens_approximately(trimmed_msgs)

            logger.info(
                f"Fallback: Using last {fallback_count} messages (~{fallback_tokens} tokens)"
            )

    try:
        # Check if we are processing a tool output (last message is a ToolMessage)
        last_msg = messages[-1] if messages else None
        if isinstance(last_msg, ToolMessage):
            # Force structured output for tool responses
            # Use a specific prompt that tells the LLM to analyze and structure, not call tools
            structured_system_msg = SystemMessage(content=STRUCTURED_OUTPUT_PROMPT)

            try:
                structured_llm = get_llm().with_structured_output(NetworkResponse, method="json_mode")
                response = structured_llm.invoke([structured_system_msg] + trimmed_msgs)

                # Convert Pydantic model to JSON string for the AIMessage
                # This ensures the next node (or UI) receives a consistent string format
                return {"messages": [AIMessage(content=response.model_dump_json())]}
            except Exception as struct_error:
                logger.error(f"Structured output error: {struct_error}")
                # Fallback: return raw tool message content if structuring fails
                return {
                    "messages": [
                        AIMessage(
                            content=f"Tool output received but could not be structured: {last_msg.content}"
                        )
                    ]
                }

        # Normal chat interaction
        inventory_str = get_device_info()
        system_msg = SystemMessage(content=UNDERSTAND_PROMPT.format(device_inventory=inventory_str))
        response = get_llm_with_tools().invoke([system_msg] + trimmed_msgs)
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
    """Request user approval for configuration changes.

    Interrupts workflow execution and waits for user decision.

    Args:
        state: Current graph state

    Returns:
        None if approved, denial message if rejected
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
                content=f"❌ User denied permission: {tool_call['name']}",
            )
        ],
    }


def planner_node(state: dict[str, Any]) -> dict[str, Any]:
    """Generate step-by-step plan for complex requests.

    Args:
        state: Current graph state

    Returns:
        Updated state with plan as AI message
    """
    messages = state.get("messages", [])
    last_msg = messages[-1]

    llm = get_llm().with_structured_output(Plan)
    prompt = PLANNER_PROMPT.format(user_request=last_msg.content)

    plan = llm.invoke(prompt)

    # Return the plan as a tool message or just context?
    # For now, let's just add it as an AIMessage so the Understand node sees it
    plan_str = "I have created a plan:\\n" + "\\n".join(
        [f"{i + 1}. {step}" for i, step in enumerate(plan.steps)]
    )
    return {"messages": [AIMessage(content=plan_str)]}
