import uuid

import chainlit as cl
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from graph.router import create_graph

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

            if kind == "on_chat_model_stream" and node_name == "respond":
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

        snapshot = graph.get_state(config)

        if not snapshot.tasks:
            break

        if not snapshot.tasks[0].interrupts:
            break

        interrupt_value = snapshot.tasks[0].interrupts[0].value
        tool_call = interrupt_value.get("tool_call", {})
        tool_name = tool_call.get("name", "Unknown Tool")
        tool_args = tool_call.get("args", {})

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

        print(f"DEBUG: Chainlit Action Response: {res}")

        if res and res.get("name") == "approve":
            resume_value = "approved"
        else:
            resume_value = "denied"

        current_input = Command(resume=resume_value)
