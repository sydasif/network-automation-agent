import os
import yaml
from dotenv import load_dotenv
from netmiko import ConnectHandler
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from typing import Dict, List, TypedDict, Annotated, Union
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from tabulate import tabulate

# Load environment variables
load_dotenv()

class State(TypedDict):
    messages: List
    results: Dict

def load_devices():
    """Load device configurations from hosts.yaml"""
    with open('config/hosts.yaml', 'r') as file:
        config = yaml.safe_load(file)
    return {device['name']: device for device in config['devices']}

@tool
def run_command(device: Union[str, List[str]], command: str) -> str:
    """Execute network command and return output from one or multiple devices"""
    all_devices = load_devices()

    # Convert single device to list for consistent processing
    if isinstance(device, str):
        device_list = [device]
    else:
        device_list = device

    # Check if all devices exist in config
    for dev in device_list:
        if dev not in all_devices:
            return f"Error: Device '{dev}' not found in configuration."

    # Execute commands in parallel using ThreadPoolExecutor
    results = {}

    def execute_on_device(dev):
        dev_config = all_devices[dev]
        try:
            connection = ConnectHandler(
                device_type=dev_config['device_type'],
                host=dev_config['host'],
                username=dev_config['username'],
                password=dev_config['password']
            )

            output = connection.send_command(command)
            connection.disconnect()

            return dev, output
        except Exception as e:
            return dev, f"Error executing command on {dev}: {str(e)}"

    # Run commands in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(execute_on_device, dev): dev for dev in device_list}

        for future in as_completed(futures):
            dev, output = future.result()
            results[dev] = output

    # Format results as a string
    result_str = ""
    for dev, output in results.items():
        result_str += f"=== Output from {dev} ===\n"
        result_str += f"{output}\n\n"

    return result_str

# Initialize the LLM
llm = ChatGroq(
    temperature=0,
    model_name="llama3-70b-8192",
    api_key=os.getenv("GROQ_API_KEY")
)

def understand_node(state):
    """Parse user intent to extract device(s) and command"""
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else ""

    # Simple parsing to extract device and command
    # In a real implementation, you'd use more sophisticated NLP
    if isinstance(last_message, dict) and "content" in last_message:
        content = last_message["content"]
    elif isinstance(last_message, str):
        content = last_message
    else:
        content = str(last_message)

    # Look for all device names in the message
    devices = load_devices()
    found_devices = []
    for device_name in devices.keys():
        # Use word boundary to avoid partial matches (e.g. "router" matching "router-1" but not "subrouter-1")
        if re.search(rf'\b{re.escape(device_name)}\b', content, re.IGNORECASE):
            found_devices.append(device_name)

    # If no specific device mentioned, default to all devices
    if not found_devices:
        found_devices = list(devices.keys())

    # Define common commands for extraction
    command_patterns = [
        (r"show version", "show version"),
        (r"show interfaces", "show interfaces"),
        (r"show ip route", "show ip route"),
        (r"show running-config", "show running-config"),
        (r"show startup-config", "show startup-config")
    ]

    found_command = None
    for pattern, command in command_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            found_command = command
            break

    # If no command found, default to show version
    if not found_command:
        found_command = "show version"

    # Store extracted intent in state
    parsed_intent = {
        "device": found_devices if len(found_devices) > 1 else found_devices[0] if found_devices else None,
        "command": found_command
    }

    device_str = ", ".join(found_devices) if isinstance(parsed_intent["device"], list) else parsed_intent["device"] or "unknown"
    return {
        "messages": [f"Understood: Run '{found_command}' on '{device_str}'"],
        "results": {"parsed_intent": parsed_intent}
    }

def execute_node(state):
    """Execute the command on the device"""
    results = state.get("results", {})
    parsed_intent = results.get("parsed_intent", {})

    device = parsed_intent.get("device")
    command = parsed_intent.get("command")

    if not device or not command:
        return {
            "messages": ["Could not parse device or command from request"],
            "results": {"error": "Missing device or command"}
        }

    # Execute the command
    command_result = run_command.invoke({"device": device, "command": command})

    return {
        "messages": [f"Executed command on {device}"],
        "results": {**results, "command_result": command_result}
    }

def parse_show_interfaces(output):
    """Parse 'show interfaces' output into structured format for tabulation"""
    lines = output.strip().split('\n')
    interfaces = []
    current_interface = {}

    for line in lines:
        # Look for interface name line (starts with interface name and has status)
        if re.match(r'^\w+(?:\d+/\d+(?:\.\d+)?)?(?:\s+is\s+.*)?$', line.strip()) and 'is' in line:
            # Save previous interface if exists
            if current_interface:
                interfaces.append(current_interface)

            # Extract interface name and status
            parts = line.split()
            if len(parts) >= 3:
                current_interface = {
                    'Interface': parts[0],
                    'Status': parts[1] if len(parts) > 1 else 'N/A',
                    'Protocol': parts[2] if len(parts) > 2 else 'N/A'
                }
        elif 'address' in line.lower() and current_interface:
            # Extract IP address if present
            ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+/\d+)', line)
            if ip_match:
                current_interface['IP Address'] = ip_match.group(1)

    # Add the last interface
    if current_interface:
        interfaces.append(current_interface)

    return interfaces

def respond_node(state):
    """Format and return results to user"""
    results = state.get("results", {})
    command_result = results.get("command_result", "No result found")

    # Check if this is a 'show interfaces' command for special formatting
    parsed_intent = results.get("parsed_intent", {})
    command = parsed_intent.get("command", "")

    if "show interfaces" in command.lower():
        # Parse the interfaces output
        # Split the result by device sections
        device_outputs = re.split(r'=+\s+Output from ', command_result)

        formatted_result = ""
        for device_output in device_outputs:
            if not device_output.strip():
                continue

            # Separate device name from output
            if '\n' in device_output:
                device_part, output_part = device_output.split('\n', 1)
                interfaces = parse_show_interfaces(output_part)

                if interfaces:
                    formatted_result += f"\n=== Interface Status for {device_part.strip(' =')} ===\n"
                    formatted_result += tabulate(interfaces, headers="keys", tablefmt="grid")
                    formatted_result += "\n"
                else:
                    formatted_result += f"\n=== Output from {device_part.strip(' =')} ===\n{output_part}\n"
            else:
                formatted_result += f"\n{device_output}\n"

        response = f"Command execution result:\n{formatted_result}"
    else:
        # For other commands, return the original result
        response = f"Command execution result:\n{command_result}"

    return {
        "messages": [response]
    }

def main():
    """Main function to create and run the LangGraph with CLI loop"""
    # Create the state graph
    workflow = StateGraph(State)

    # Add nodes
    workflow.add_node("understand", understand_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("respond", respond_node)

    # Define edges
    workflow.add_edge("understand", "execute")
    workflow.add_edge("execute", "respond")

    # Set entry point and end point
    workflow.set_entry_point("understand")

    # Compile the graph
    app = workflow.compile()

    print("Network AI Agent ready! Type 'quit' to exit.")

    while True:
        try:
            user_input = input("\nEnter your command: ").strip()

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break

            if not user_input:
                continue

            # Process the user input through the graph
            final_state = app.invoke({"messages": [user_input], "results": {}})

            print("\nResponse:")
            for msg in final_state["messages"]:
                print(f"- {msg}")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()