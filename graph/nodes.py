"""Defines the node functions for the network automation agent workflow.

This module implements the three main nodes in the LangGraph workflow:
- understand_node: Parses user input and determines if tools need to be executed
- execute_node: Executes network commands on specified devices
- respond_node: Formats and returns results to the user
"""

from typing import List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from llm.setup import create_llm
from tools.run_command import run_command
from utils.devices import load_devices

llm = create_llm()
llm_with_tools = llm.bind_tools([run_command])


# Cache for device names to avoid repeated loading in understand_node
_CACHED_DEVICE_NAMES: list[str] | None = None


def clear_device_cache():
    """Clear the cached device names to force reloading from configuration."""
    global _CACHED_DEVICE_NAMES
    _CACHED_DEVICE_NAMES = None


def understand_node(state: dict) -> dict:
    """Processes user input and determines if network commands need to be executed.

    This node analyzes the conversation history and creates an appropriate
    system message with available devices. It then uses the LLM to decide
    whether to call tools (execute commands) or respond directly to the user.

    Args:
        state: The current state of the conversation containing messages and results

    Returns:
        Updated state with new messages and preserved results
    """
    global _CACHED_DEVICE_NAMES

    messages: list[str] = state.get("messages", [])

    # Use cached device names if available, otherwise load and cache them
    if _CACHED_DEVICE_NAMES is None:
        devices = load_devices()  # This will use the cached version from utils/devices
        _CACHED_DEVICE_NAMES = list(devices.keys())

    system_msg = SystemMessage(
        content=(
            "You are a network automation assistant.\n"
            f"Available devices: {', '.join(_CACHED_DEVICE_NAMES)}\n"
            "If user asks to run show commands, call run_command tool."
        )
    )

    full_messages = [system_msg]
    for m in messages:
        if isinstance(m, str):
            full_messages.append(HumanMessage(content=m))
        else:
            full_messages.append(m)

    response = llm_with_tools.invoke(full_messages)

    return {"messages": messages + [response], "results": state.get("results", {})}


def should_execute_tools(state: dict) -> str:
    """Determines if the workflow should execute tools or respond directly.

    This function checks if the last message in the state contains tool calls
    that need to be executed.

    Args:
        state: The current state of the conversation

    Returns:
        String indicating the next step: "execute" if tools need to run, "respond" otherwise
    """
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "execute"
    return "respond"


def execute_node(state: dict) -> dict:
    """Executes network commands on specified devices based on tool calls.

    This node processes tool calls from the LLM, specifically the run_command tool,
    and executes the requested commands on the specified devices. It handles
    the parallel execution of commands and formats the results as tool messages.

    Args:
        state: The current state containing messages with tool calls

    Returns:
        Updated state with tool response messages and preserved results
    """
    messages = state["messages"]
    last = messages[-1]

    from langchain_core.messages import ToolMessage

    tool_results = []
    if hasattr(last, "tool_calls"):
        for tool_call in last.tool_calls:
            if tool_call["name"] == "run_command":
                # tool_call["args"] is the dict of arguments the tool expects
                result = run_command.invoke(tool_call["args"])
                tool_results.append({"tool_call_id": tool_call["id"], "output": result})

    # Create ToolMessage objects to pass results back to the LLM
    # Pre-allocate list with known size to avoid dynamic resizing
    tool_messages = []
    tool_messages_append = tool_messages.append  # Cache the append method
    for tr in tool_results:
        tool_messages_append(
            ToolMessage(content=str(tr["output"]), tool_call_id=tr["tool_call_id"])
        )

    return {"messages": messages + tool_messages, "results": state.get("results", {})}


def respond_node(state: dict) -> dict:
    """Formats and returns the final response to the user.

    This node synthesizes the results from command execution or provides
    a direct response if no tools were needed. It creates a system message
    that guides the LLM to format the output appropriately.

    Args:
        state: The current state containing messages and results

    Returns:
        Updated state with the final response message and preserved results
    """
    messages = state["messages"]
    last = messages[-1]

    if isinstance(last, AIMessage) and not hasattr(last, "tool_calls"):
        return state

    synthesis_prompt = SystemMessage(
        content=(
            "Analyze the command results and provide a concise summary. "
            "If structured, prefer tables. If raw, extract key lines."
        )
    )

    response = llm.invoke(messages + [synthesis_prompt])

    return {"messages": messages + [response], "results": state.get("results", {})}
