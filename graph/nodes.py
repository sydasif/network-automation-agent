"""Defines the node functions for the network automation agent workflow.

This module implements the three main nodes in the LangGraph workflow that
handle the conversational flow of the network automation agent:

1. understand_node: Analyzes user input and determines whether to execute
   network commands or respond directly to the user. It uses an LLM to
   understand intent and generate appropriate system prompts with available
   device information.

2. execute_node: Processes LLM-generated tool calls by executing the
   requested network commands on specified devices using the run_command tool.
   This node handles parallel execution and formats results appropriately.

3. respond_node: Generates the final response to the user, either from
   command execution results or as a direct response to the user's input.
   This node synthesizes the information and formats it according to the
   configured response prompt.

The nodes work together to create a seamless experience where users can
interact with network devices using natural language.
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

# Initialize the LLM and bind the run_command tool for use in the understand node
llm = create_llm()
llm_with_tools = llm.bind_tools([run_command])


def understand_node(state: dict[str, Any]) -> dict[str, Any]:
    """Processes user input and determines if network commands need to be executed.

    Analyzes the conversation history, retrieves available device names from the
    database, and constructs a system message that includes this information.
    Then uses the LLM to interpret the user's intent and decides whether to
    call tools (execute commands) or respond directly to the user.

    Memory management is implemented using message trimming to keep within
    the LLM's context window while preserving conversation context. The
    original message history is maintained in the LangGraph checkpoint system.

    Args:
        state: Current conversation state containing message history

    Returns:
        Updated state with new messages from the LLM decision
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

    Processes tool calls from the LLM's understanding phase. Specifically handles
    the 'run_command' tool by extracting arguments and invoking the appropriate
    command execution. Results are formatted as tool messages that can be
    consumed by the response node.

    Parallel execution is managed by the run_command tool itself, allowing
    multiple network commands to be executed concurrently when possible.

    Args:
        state: Current state containing messages with tool calls

    Returns:
        Updated state with tool response messages formatted as ToolMessage objects
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

    Synthesizes the results from command execution or provides a direct response
    if no tools were needed. Uses the configured response prompt to guide the
    LLM in formatting output appropriately, whether as structured data, tables,
    or natural language responses.

    Args:
        state: Current state containing messages including tool responses

    Returns:
        Updated state with the final AI response message formatted for the user
    """
    # For the response node, we might want the last few messages to contextually answer
    messages = state["messages"]

    # Optional: Trim here too if output is huge, but usually safe to pass last few
    synthesis_prompt = SystemMessage(content=RESPOND_PROMPT)

    # We pass the full (or trimmed) history + the instruction to summarize
    response = llm.invoke(messages + [synthesis_prompt])

    return {"messages": [response]}  # Returns only new message
