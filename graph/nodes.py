"""Defines the node functions for the network automation agent workflow.

This module implements the three main nodes in the LangGraph workflow:
- understand_node: Parses user input and determines if tools need to be executed
- execute_node: Executes network commands on specified devices
- respond_node: Formats and returns results to the user
"""

from typing import Any

from langchain_core.messages import (
    SystemMessage,
    ToolMessage,
    trim_messages,
)

from graph.prompts import RESPOND_PROMPT, UNDERSTAND_PROMPT
from llm.client import create_llm
from tools.run_command import run_command
from utils.database import get_db
from utils.devices import get_all_device_names

llm = create_llm()
llm_with_tools = llm.bind_tools([run_command])


def understand_node(state: dict[str, Any]) -> dict[str, Any]:
    """Processes user input and determines if network commands need to be executed.

    This node analyzes the conversation history and creates an appropriate
    system message with available devices. It then uses the LLM to decide
    whether to call tools (execute commands) or respond directly to the user.

    Args:
        state: The current state of the conversation containing messages.

    Returns:
        Updated state with new messages.
    """
    messages = state.get("messages", [])

    # --- KISS MEMORY MANAGEMENT ---
    # We trim messages strictly for the LLM context window here.
    # The full history is still safely stored in the Checkpointer (database).
    # Using len as token counter since transformers might not be available
    trimmed_messages = trim_messages(
        messages,
        max_tokens=2000,  # Adjust based on your model's limit
        strategy="last",
        token_counter=len,  # Use len as simple fallback, or install transformers
        start_on="human",
        end_on=("human", "ai"),
        include_system=False,  # We will add system prompt manually below
    )

    with get_db() as db:
        device_names = get_all_device_names(db)

    system_msg = SystemMessage(
        content=UNDERSTAND_PROMPT.format(device_names=", ".join(device_names))
    )

    # Reconstruct: System Prompt + Trimmed History
    full_messages = [system_msg] + trimmed_messages

    response = llm_with_tools.invoke(full_messages)

    # Because we used add_messages in router.py, we just return the NEW message
    return {"messages": [response]}


def execute_node(state: dict[str, Any]) -> dict[str, Any]:
    """Executes network commands on specified devices based on tool calls.

    This node processes tool calls from the LLM, specifically the run_command tool,
    and executes the requested commands on the specified devices. It handles
    the parallel execution of commands and formats the results as tool messages.

    Args:
        state: The current state containing messages with tool calls

    Returns:
        Updated state with tool response messages.
    """
    messages = state["messages"]
    last = messages[-1]

    tool_results = []
    if hasattr(last, "tool_calls"):
        for tool_call in last.tool_calls:
            if tool_call["name"] == "run_command":
                result = run_command.invoke(tool_call["args"])
                tool_results.append({"tool_call_id": tool_call["id"], "output": result})

    tool_messages = [
        ToolMessage(content=str(tr["output"]), tool_call_id=tr["tool_call_id"])
        for tr in tool_results
    ]

    return {"messages": tool_messages}


def respond_node(state: dict[str, Any]) -> dict[str, Any]:
    """Formats and returns the final response to the user.

    This node synthesizes the results from command execution or provides
    a direct response if no tools were needed. It creates a system message
    that guides the LLM to format the output appropriately.

    Args:
        state: The current state containing messages.

    Returns:
        Updated state with the final response message.
    """
    # For the response node, we might want the last few messages to contextually answer
    messages = state["messages"]

    # Optional: Trim here too if output is huge, but usually safe to pass last few
    synthesis_prompt = SystemMessage(content=RESPOND_PROMPT)

    # We pass the full (or trimmed) history + the instruction to summarize
    response = llm.invoke(messages + [synthesis_prompt])

    return {"messages": [response]}  # Returns only new message
