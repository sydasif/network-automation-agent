# Network AI Agent

A sophisticated network automation tool that combines AI with network device management to provide intelligent command execution and monitoring across multiple network devices.

## Features

- **AI-Powered Network Commands**: Natural language interface for network device management
- **Multi-Device Support**: Execute commands across multiple devices simultaneously
- **Parallel Execution**: Efficient parallel processing using ThreadPoolExecutor
- **Structured Output**: Pretty-formatted output with tabulate, especially for interface data
- **LangGraph Integration**: State machine for managing complex network workflows
- **Secure Device Access**: SSH connectivity using netmiko for secure device communication

## Prerequisites

- Python 3.8 or higher
- uv package manager
- Access to network devices via SSH
- Groq API key for AI functionality

## Setup

1. **Clone and Initialize**:

   ```bash
   git clone <repository-url>
   cd network-agent
   ```

2. **Install Dependencies**:

   ```bash
   uv sync
   ```

3. **Configure Environment**:

   ```bash
   cp .env.example .env
   ```

   Add your Groq API key to the `.env` file.

4. **Configure Devices**:
   Edit `hosts.yaml` to add your network devices:

   ```yaml
   devices:
     - name: router-1
       host: 192.168.1.10
       username: admin
       password: password123
       device_type: cisco_ios
     - name: switch-1
       host: 192.168.1.11
       username: admin
       password: password123
       device_type: cisco_ios
   ```

## Usage

Run the agent:

```bash
uv run main.py
```

The agent will start in interactive mode. You can enter commands like:

- "Show me the version of router-1"
- "Show interfaces on switch-1"
- "Show version on all devices"
- "Show running-config on router-1 and switch-1"

Type `quit` to exit.

## Architecture

The agent follows a LangGraph-based state machine approach with three main nodes:

1. **Understand**: Parses user intent to extract device names and commands
2. **Execute**: Runs the network commands on the specified devices
3. **Respond**: Formats and returns results to the user

## API Documentation

### Core Modules

- `main.py`: Entry point with interactive CLI interface
- `graph/router.py`: Workflow definition using LangGraph
- `graph/nodes.py`: Implementation of the three main nodes
- `llm/setup.py`: LLM client configuration and initialization
- `tools/run_command.py`: Network command execution tool
- `utils/devices.py`: Device configuration loading utilities

### Key Functions

- `create_graph()`: Creates the LangGraph workflow
- `understand_node()`: Processes user input and determines if tools need to be executed
- `execute_node()`: Executes network commands on specified devices
- `respond_node()`: Formats and returns results to the user
- `run_command()`: Executes commands on network devices via SSH
- `load_devices()`: Loads device configurations from hosts.yaml

## Supported Commands

The agent can execute any command supported by your network devices, with special formatting for:

- `show version`
- `show interfaces`
- `show ip route`
- `show running-config`
- `show startup-config`

## Security

- Device credentials are stored in `hosts.yaml`
- API keys are stored in `.env` and not committed to version control
- SSH connections are established using the netmiko library with secure practices

## Troubleshooting

- Ensure your `.env` file contains a valid Groq API key
- Verify network connectivity to configured devices
- Check device credentials in `hosts.yaml`
- Confirm the device type matches your network equipment in the configuration

## License
