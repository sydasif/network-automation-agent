from typing import List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from llm.setup import create_llm
from tools.run_command import run_command
from utils.devices import load_devices

llm = create_llm()
llm_with_tools = llm.bind_tools([run_command])


def understand_node(state: dict) -> dict:
    messages: list[str] = state.get("messages", [])

    devices = load_devices()
    device_names = list(devices.keys())

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


def should_execute_tools(state: dict) -> str:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "execute"
    return "respond"


def execute_node(state: dict) -> dict:
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

    tool_messages = [
        ToolMessage(content=str(tr["output"]), tool_call_id=tr["tool_call_id"])
        for tr in tool_results
    ]

    return {"messages": messages + tool_messages, "results": state.get("results", {})}


def respond_node(state: dict) -> dict:
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
