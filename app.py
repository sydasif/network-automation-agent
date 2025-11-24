"""Network AI Agent Web UI entry point.

This module implements the Chainlit web interface for the Network AI Agent,
providing a chat interface for users to interact with the agent and manage
network devices through natural language commands.
"""

import json
import uuid

import chainlit as cl
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from agent.nodes import NODE_UNDERSTAND, RESUME_APPROVED, RESUME_DENIED
from agent.workflow import create_graph, get_approval_request

# Initialize graph once to avoid overhead - this creates the workflow when the module loads
graph = create_graph()


@cl.on_chat_start
async def start():
    """Initialize a new chat session with a unique thread ID."""
    # Unique thread ID per session
    thread_id = str(uuid.uuid4())
    cl.user_session.set("config", {"configurable": {"thread_id": thread_id}})
    await cl.Message(content="👋 **Network AI Agent Ready!**\n").send()


@cl.on_message
async def on_message(message: cl.Message):
    """Handle incoming messages from the user in the chat interface.

    Processes the user's message through the agent workflow, streams the
    LLM's response, handles tool execution, and requests approval for
    configuration changes.

    Args:
        message: The message object containing the user's input.
    """
    config = cl.user_session.get("config")

    # Send user input to the graph as a HumanMessage
    current_input = {"messages": [HumanMessage(content=message.content)]}

    # Main processing loop - handles streaming responses and approval requests
    while True:
        final_msg = cl.Message(content="")
        has_streamed = False

        # Stream events from the graph for real-time updates
        async for event in graph.astream_events(current_input, config, version="v2"):
            kind = event["event"]
            metadata = event.get("metadata", {})
            node_name = metadata.get("langgraph_node", "")

            # 1. Stream the LLM's thought process/answer as it's generated
            if kind == "on_chat_model_stream" and node_name == NODE_UNDERSTAND:
                content = event["data"]["chunk"].content
                if content:
                    if not has_streamed:
                        await final_msg.send()
                        has_streamed = True
                    await final_msg.stream_token(content)

            # 2. Show tool execution status when tools are invoked
            elif kind == "on_tool_start":
                tool_name = event["name"]
                async with cl.Step(name=tool_name) as step:
                    step.input = event["data"].get("input")

        if has_streamed:
            await final_msg.update()

        # Check if the graph paused for approval (for config commands)
        snapshot = graph.get_state(config)
        tool_call = get_approval_request(snapshot)

        # If no pending approval request, exit the loop and finish processing
        if not tool_call:
            break

        # Format arguments for readability (handling lists/batching)
        tool_name = tool_call.get("name", "Unknown Tool")
        tool_args = tool_call.get("args", {})
        pretty_args = json.dumps(tool_args, indent=2)

        # Ask the user for permission to execute the configuration change
        res = await cl.AskActionMessage(
            content=f"⚠️ **Approval Required**\n\nThe agent wants to execute:\n\n**Tool:** `{tool_name}`\n```json\n{pretty_args}\n```",
            actions=[
                cl.Action(
                    name="approve",
                    value="approve",
                    payload={"value": "approve"},
                    label="✅ Approve",
                ),
                cl.Action(name="deny", value="deny", payload={"value": "deny"}, label="❌ Deny"),
            ],
        ).send()

        # Resume the graph with the user's decision (approved or denied)
        resume_value = RESUME_APPROVED if res and res.get("name") == "approve" else RESUME_DENIED
        current_input = Command(resume=resume_value)
