"""Defines the node functions for the network automation agent workflow.

This module implements the three main nodes in the LangGraph workflow:
- understand_node: Parses user input and determines if tools need to be executed
- execute_node: Executes network commands on specified devices
- respond_node: Formats and returns results to the user
"""

from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from llm.setup import create_llm
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
        state: The current state of the conversation containing messages and results

    Returns:
        Updated state with new messages and preserved results
    """
    messages: list[BaseMessage] = state.get("messages", [])

    with get_db() as db:
        device_names = get_all_device_names(db)

    system_msg = SystemMessage(
        content=(
            "You are a network automation assistant.\n"
            f"Available devices: {', '.join(device_names)}\n"
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

def execute_node(state: dict[str, Any]) -> dict[str, Any]:
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


def respond_node(state: dict[str, Any]) -> dict[str, Any]:
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
            "If structured, prefer tables. If raw, extract key lines. "
            "Break down each device's output separately."
        )
    )

    response = llm.invoke(messages + [synthesis_prompt])

    return {"messages": messages + [response], "results": state.get("results", {})}
