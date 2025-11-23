import logging
import uuid

import chainlit as cl
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from graph.router import create_graph

# Setup minimal logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Initialize the graph once at startup
graph = create_graph()


@cl.on_chat_start
async def start():
    """
    Initializes the user session.
    Generates a unique thread_id so multiple users don't share state.
    """
    thread_id = str(uuid.uuid4())
    cl.user_session.set("config", {"configurable": {"thread_id": thread_id}})

    await cl.Message(
        content='👋 **Network AI Agent Ready!**\n\nI can help you configure devices, check status, or troubleshoot.\n\nTry asking:\n*"Show version on sw1"*\n*"Shutdown interface Gi0/1 on sw1"*'
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """
    Main chat loop.
    Handles the lifecycle of: Input -> Streaming -> Interrupt (Approval) -> Resume -> Output.
    """
    config = cl.user_session.get("config")

    # Prepare the initial input to the graph
    current_input = {"messages": [HumanMessage(content=message.content)]}

    # We use a loop to handle the "Pause -> Resume" cycle required by LangGraph interrupts
    while True:
        # Create a placeholder for the response bubble.
        final_msg = cl.Message(content="")
        has_streamed = False

        # 1. Run the graph and stream events
        async for event in graph.astream_events(current_input, config, version="v2"):
            kind = event["event"]
            metadata = event.get("metadata", {})
            node_name = metadata.get("langgraph_node", "")

            # --- STREAMING LOGIC ---
            # We only stream content from the 'respond' node.
            if kind == "on_chat_model_stream" and node_name == "respond":
                content = event["data"]["chunk"].content
                if content:
                    if not has_streamed:
                        await final_msg.send()
                        has_streamed = True
                    await final_msg.stream_token(content)

            # --- TOOL VISUALIZATION ---
            elif kind == "on_tool_start":
                tool_name = event["name"]
                async with cl.Step(name=tool_name) as step:
                    step.input = event["data"].get("input")

        # Close the stream properly if we sent any text
        if has_streamed:
            await final_msg.update()

        # 2. Check for Interrupts (Human-in-the-Loop)
        snapshot = graph.get_state(config)

        # If no tasks exist, the graph finished successfully. Break the loop.
        if not snapshot.tasks:
            break

        # If tasks exist but no interrupts, it's just running (safety check).
        if not snapshot.tasks[0].interrupts:
            break

        # 3. Handle the Approval Request
        interrupt_value = snapshot.tasks[0].interrupts[0].value
        tool_call = interrupt_value.get("tool_call", {})
        tool_name = tool_call.get("name", "Unknown Tool")
        tool_args = tool_call.get("args", {})

        # Show the "Approve/Deny" buttons
        # We keep the 'payload' here because your version requires it
        res = await cl.AskActionMessage(
            content=f"⚠️ **Approval Required**\n\nThe agent wants to execute:\n\n**Tool:** `{tool_name}`\n**Args:** `{tool_args}`",
            actions=[
                cl.Action(
                    name="approve",
                    value="approved",
                    payload={"value": "approved"},
                    label="✅ Approve",
                    description="Execute command",
                ),
                cl.Action(
                    name="deny",
                    value="denied",
                    payload={"value": "denied"},
                    label="❌ Deny",
                    description="Stop execution",
                ),
            ],
        ).send()

        # 4. Determine Resume Value
        # The value is nested in the payload, not directly in res
        if res and res.get("payload", {}).get("value") == "approved":
            resume_value = "approved"
        else:
            resume_value = "denied"

        # 5. Resume the Graph
        current_input = Command(resume=resume_value)
