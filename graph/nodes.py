"""Node functions for the LangGraph workflow."""

from typing import Any
from langchain_core.messages import SystemMessage, ToolMessage, trim_messages
from langgraph.types import interrupt  # <--- THE BUILT-IN HITL FEATURE

from graph.prompts import RESPOND_PROMPT, UNDERSTAND_PROMPT
from llm.client import create_llm
from tools.commands import show_command, config_command
from utils.database import get_db
from utils.devices import get_all_device_names

llm = create_llm()
llm_with_tools = llm.bind_tools([show_command, config_command])


def understand_node(state: dict[str, Any]) -> dict[str, Any]:
    """Analyzes user intent and selects appropriate tools based on context.

    This node processes the conversation history, trims the context to avoid
    exceeding token limits, retrieves available device names from the database,
    and invokes the LLM to determine which tools to call based on the user's request.

    Args:
        state: Current state containing messages and results.

    Returns:
        Dictionary with updated messages including tool calls or direct responses.
    """
    messages = state.get("messages", [])

    # Trim context to last 2000 tokens to prevent exceeding model token limits
    # Uses "last" strategy to keep most recent messages, starting from human input
    # and ending with either human or AI messages, excluding system messages
    trimmed_messages = trim_messages(
        messages,
        max_tokens=2000,
        strategy="last",
        token_counter=len,  # Using len as a simple character counter
        start_on="human",   # Start trimming from human messages
        end_on=("human", "ai"),  # End trimming at human or AI messages
        include_system=False,    # Exclude system messages from token count
    )

    with get_db() as db:
        device_names = get_all_device_names(db)

    system_msg = SystemMessage(
        content=UNDERSTAND_PROMPT.format(device_names=", ".join(device_names))
    )

    response = llm_with_tools.invoke([system_msg] + trimmed_messages)
    return {"messages": [response]}


def execute_read_node(state: dict[str, Any]) -> dict[str, Any]:
    """Executes read-only commands (show_command) without requiring approval.

    This node processes tool calls for read-only operations such as show commands
    on network devices. It executes the commands and returns the results without
    requiring human intervention.

    Args:
        state: Current state containing messages and results.

    Returns:
        Dictionary with ToolMessage responses containing the command results.
    """
    messages = state["messages"]
    last_msg = messages[-1]
    tool_results = []

    if hasattr(last_msg, "tool_calls"):
        for tool_call in last_msg.tool_calls:
            if tool_call["name"] == "show_command":
                result = show_command.invoke(tool_call["args"])
                tool_results.append({"tool_call_id": tool_call["id"], "output": result})

    return {
        "messages": [
            ToolMessage(content=str(tr["output"]), tool_call_id=tr["tool_call_id"])
            for tr in tool_results
        ]
    }


def execute_write_node(state: dict[str, Any]) -> dict[str, Any]:
    """Executes configuration commands that require human approval.

    This node handles configuration changes on network devices. It implements
    a human-in-the-loop (HITL) workflow where configuration commands are paused
    for user approval before execution. The node waits for a resume command
    indicating whether to proceed with the changes or deny them.

    Args:
        state: Current state containing messages and results.

    Returns:
        Dictionary with ToolMessage responses containing the command results
        or approval denial message.
    """
    messages = state["messages"]
    last_msg = messages[-1]
    tool_results = []

    if hasattr(last_msg, "tool_calls"):
        for tool_call in last_msg.tool_calls:
            if tool_call["name"] == "config_command":
                # --- BUILT-IN HITL MIDDLEWARE ---
                # 1. Pause execution and send payload to client
                # 2. Wait for Command(resume="yes/no")
                # 3. "decision" variable gets the value when resumed
                decision = interrupt({"type": "approval_request", "tool_call": tool_call})

                if decision == "approved":
                    # Execute if approved
                    result = config_command.invoke(tool_call["args"])
                    output = result
                else:
                    # Handle rejection
                    output = "User denied the configuration request."

                tool_results.append({"tool_call_id": tool_call["id"], "output": output})

    return {
        "messages": [
            ToolMessage(content=str(tr["output"]), tool_call_id=tr["tool_call_id"])
            for tr in tool_results
        ]
    }


def respond_node(state: dict[str, Any]) -> dict[str, Any]:
    """Formats and generates the final response to the user.

    This node takes the processed results from previous nodes and generates
    a human-readable response for the user. It uses the LLM to synthesize
    the information and present it in a clear, concise format.

    Args:
        state: Current state containing messages and results.

    Returns:
        Dictionary with the final response message to be displayed to the user.
    """
    messages = state["messages"]
    synthesis_prompt = SystemMessage(content=RESPOND_PROMPT)
    response = llm.invoke(messages + [synthesis_prompt])
    return {"messages": [response]}
