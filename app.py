import uuid

import chainlit as cl
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from graph.consts import NODE_RESPOND, RESUME_APPROVED, RESUME_DENIED
from graph.router import create_graph
from utils.graph import get_approval_request

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

    await cl.Message(content="👋 **Network AI Agent Ready!**\n").send()


@cl.on_message
async def on_message(message: cl.Message):
    """
    Main chat loop.
    Handles the lifecycle of: Input -> Streaming -> Interrupt (Approval) -> Resume -> Output.
    """
    config = cl.user_session.get("config")

    current_input = {"messages": [HumanMessage(content=message.content)]}

    while True:
        final_msg = cl.Message(content="")
        has_streamed = False

        async for event in graph.astream_events(current_input, config, version="v2"):
            kind = event["event"]
            metadata = event.get("metadata", {})
            node_name = metadata.get("langgraph_node", "")

            # DRY: Use constant NODE_RESPOND
            if kind == "on_chat_model_stream" and node_name == NODE_RESPOND:
                content = event["data"]["chunk"].content
                if content:
                    if not has_streamed:
                        await final_msg.send()
                        has_streamed = True
                    await final_msg.stream_token(content)

            elif kind == "on_tool_start":
                tool_name = event["name"]
                async with cl.Step(name=tool_name) as step:
                    step.input = event["data"].get("input")

        if has_streamed:
            await final_msg.update()

        # DRY: Use helper function
        snapshot = graph.get_state(config)
        tool_call = get_approval_request(snapshot)

        if not tool_call:
            break

        tool_name = tool_call.get("name", "Unknown Tool")
        tool_args = tool_call.get("args", {})

        # DRY: Use constants for values and payloads
        res = await cl.AskActionMessage(
            content=f"⚠️ **Approval Required**\n\nThe agent wants to execute:\n\n**Tool:** `{tool_name}`\n**Args:** `{tool_args}`",
            actions=[
                cl.Action(
                    name="approve",
                    value=RESUME_APPROVED,
                    payload={"value": RESUME_APPROVED},
                    label="✅ Approve",
                    description="Execute command",
                ),
                cl.Action(
                    name="deny",
                    value=RESUME_DENIED,
                    payload={"value": RESUME_DENIED},
                    label="❌ Deny",
                    description="Stop execution",
                ),
            ],
        ).send()

        print(f"DEBUG: Chainlit Action Response: {res}")

        if res and res.get("name") == "approve":
            resume_value = RESUME_APPROVED
        else:
            resume_value = RESUME_DENIED

        current_input = Command(resume=resume_value)
