import uuid

import chainlit as cl
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from agent.nodes import NODE_UNDERSTAND, RESUME_APPROVED, RESUME_DENIED
from agent.workflow import create_graph, get_approval_request

graph = create_graph()


@cl.on_chat_start
async def start():
    thread_id = str(uuid.uuid4())
    cl.user_session.set("config", {"configurable": {"thread_id": thread_id}})
    await cl.Message(content="👋 **Network AI Agent Ready!**\n").send()


@cl.on_message
async def on_message(message: cl.Message):
    config = cl.user_session.get("config")
    current_input = {"messages": [HumanMessage(content=message.content)]}

    while True:
        final_msg = cl.Message(content="")
        has_streamed = False

        async for event in graph.astream_events(current_input, config, version="v2"):
            kind = event["event"]
            metadata = event.get("metadata", {})
            node_name = metadata.get("langgraph_node", "")

            # Listen to NODE_UNDERSTAND for final output
            if kind == "on_chat_model_stream" and node_name == NODE_UNDERSTAND:
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
        tool_call = get_approval_request(snapshot)

        if not tool_call:
            break

        tool_name = tool_call.get("name", "Unknown Tool")
        tool_args = tool_call.get("args", {})

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

        resume_value = RESUME_APPROVED if res and res.get("name") == "approve" else RESUME_DENIED
        current_input = Command(resume=resume_value)
