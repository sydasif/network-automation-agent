import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, TypedDict, Union

import yaml
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph
from netmiko import ConnectHandler
from tabulate import tabulate

# Load environment variables
load_dotenv()


class State(TypedDict):
    messages: list
    results: dict


def load_devices():
    """Load device configurations from hosts.yaml"""
    with open('config/hosts.yaml') as file:
        config = yaml.safe_load(file)
    return {device['name']: device for device in config['devices']}


@tool
def run_command(device: str | list[str], command: str) -> str:
    """Execute network command and return output from one or multiple devices.

    Args:
        device: Single device name (str) or list of device names
        command: The CLI command to execute (e.g., 'show version', 'show interfaces')

    Returns:
        JSON formatted string with command output from each device
    """
    all_devices = load_devices()

    # Convert single device to list for consistent processing
    if isinstance(device, str):
        device_list = [device]
    else:
        device_list = device

    # Check if all devices exist in config
    for dev in device_list:
        if dev not in all_devices:
            return json.dumps({
                "error": f"Device '{dev}' not found",
                "available_devices": list(all_devices.keys()),
            })

    results = {}

    def execute_on_device(dev):
        dev_config = all_devices[dev]
        try:
            connection = ConnectHandler(
                device_type=dev_config['device_type'],
                host=dev_config['host'],
                username=dev_config['username'],
                password=dev_config['password'],
                timeout=30,
            )

            # Try structured parsing first with TextFSM
            try:
                output = connection.send_command(command, use_textfsm=True)

                # Check if TextFSM parsing worked (returns list/dict) or failed (returns string)
                if isinstance(output, str):
                    # Parsing failed, return raw text
                    parsed_type = "raw"
                    parsed_output = output
                else:
                    # Parsing succeeded
                    parsed_type = "structured"
                    parsed_output = output

            except Exception as parse_error:
                # TextFSM parsing error, fallback to raw
                output = connection.send_command(command)
                parsed_type = "raw"
                parsed_output = output

            connection.disconnect()

            return dev, {"success": True, "type": parsed_type, "data": parsed_output}

        except Exception as e:
            return dev, {"success": False, "error": str(e)}

    # Run commands in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(execute_on_device, dev): dev for dev in device_list}

        for future in as_completed(futures):
            dev, output = future.result()
            results[dev] = output

    # Return as JSON for LLM to parse
    return json.dumps({"command": command, "devices": results}, indent=2)


# Initialize the LLM
llm = ChatGroq(
    temperature=0, model_name="openai/gpt-oss-20b", api_key=os.getenv("GROQ_API_KEY")
)

# Bind the tool to the LLM
llm_with_tools = llm.bind_tools([run_command])


def understand_node(state: State) -> State:
    """Use LLM to understand user intent and decide what to do"""
    messages = state.get("messages", [])

    # Get available devices
    devices = load_devices()
    device_names = list(devices.keys())

    # Create system message with context
    system_msg = SystemMessage(
        content=f"""You are a network automation assistant. You help users interact with network devices.

Available devices: {', '.join(device_names)}

When users ask about network devices:
1. If they want information (show commands), use the run_command tool
2. If they ask about which devices are available, just tell them
3. If they're just chatting (hi, hello, thanks), respond naturally WITHOUT using tools

Common commands:
- show version (device info)
- show ip route (routing table)
- show running-config (current config)
- show interfaces status (interface status)
- show interfaces (detailed interface info)
- show ip interface brief (quick interface/IP overview)
- show mac address-table (MAC addresses)
- show cdp neighbors (connected devices)
- show vlan brief (VLAN info)
- show logging (logs)


The run_command tool returns JSON data. When data is "structured", it's been parsed by TextFSM into clean JSON.
When it's "raw", you'll need to parse the text yourself.

If no specific device is mentioned, assume they mean ALL devices: {device_names}
"""
    )

    # Add system message and convert user messages
    full_messages = [system_msg]
    for msg in messages:
        if isinstance(msg, str):
            full_messages.append(HumanMessage(content=msg))
        else:
            full_messages.append(msg)

    # Get LLM response
    response = llm_with_tools.invoke(full_messages)

    # Store the response
    new_messages = messages + [response]

    return {"messages": new_messages, "results": state.get("results", {})}


def should_execute_tools(state: State) -> str:
    """Router: Check if we need to execute tools or respond directly"""
    last_message = state["messages"][-1]

    # If LLM wants to use tools, go to execute node
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "execute"
    return "respond"


def execute_node(state: State) -> State:
    """Execute the tools that the LLM requested"""
    messages = state["messages"]
    last_message = messages[-1]

    # Execute each tool call
    tool_results = []
    if hasattr(last_message, 'tool_calls'):
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            if tool_name == "run_command":
                result = run_command.invoke(tool_args)
                tool_results.append({"tool_call_id": tool_call["id"], "output": result})

    # Create tool messages
    from langchain_core.messages import ToolMessage

    tool_messages = [
        ToolMessage(content=str(tr["output"]), tool_call_id=tr["tool_call_id"])
        for tr in tool_results
    ]

    return {"messages": messages + tool_messages, "results": state.get("results", {})}


def respond_node(state: State) -> State:
    """Have LLM create final response to user"""
    messages = state["messages"]

    # If the last message is from the LLM (no tool calls), use it directly
    last_message = messages[-1]
    if isinstance(last_message, AIMessage) and not hasattr(last_message, 'tool_calls'):
        return state

    # Otherwise, ask LLM to synthesize tool results into a response
    synthesis_prompt = SystemMessage(
        content="""Analyze the command results and provide a clear, helpful summary.

If the data is structured (type: "structured"), format it as tables when appropriate using markdown.
If the data is raw text, extract and present the key information clearly.

For interface data: show status, IP addresses, and any issues.
For version data: show model, IOS version, and uptime.
For routing data: summarize routes and highlight anything unusual.

Be concise but thorough. Use tables, bullets, or paragraphs as appropriate."""
    )

    response = llm.invoke(messages + [synthesis_prompt])

    return {"messages": messages + [response], "results": state.get("results", {})}


def create_graph():
    """Create and compile the LangGraph"""
    workflow = StateGraph(State)

    # Add nodes
    workflow.add_node("understand", understand_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("respond", respond_node)

    # Define edges
    workflow.set_entry_point("understand")
    workflow.add_conditional_edges(
        "understand", should_execute_tools, {"execute": "execute", "respond": END}
    )
    workflow.add_edge("execute", "respond")
    workflow.add_edge("respond", END)

    return workflow.compile()


def main():
    """Main CLI loop"""
    app = create_graph()

    print("🤖 Network AI Agent Ready! (with TextFSM parsing)")
    print("Available devices:", ", ".join(load_devices().keys()))
    print("Type 'quit' to exit.\n")

    conversation_history = []

    while True:
        try:
            user_input = input("You: ").strip()

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break

            if not user_input:
                continue

            # Add user message to history
            conversation_history.append(user_input)

            # Run the graph
            result = app.invoke({"messages": conversation_history, "results": {}})

            # Get the final AI message
            final_message = result["messages"][-1]
            if isinstance(final_message, AIMessage):
                response_text = final_message.content
            else:
                response_text = str(final_message)

            print(f"\n🤖 Agent: {response_text}\n")

            # Update conversation history with the full message chain
            conversation_history = result["messages"]

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}\n")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    main()
