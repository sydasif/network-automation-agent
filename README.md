# Network AI Agent

## Why Network AI Agent?

In today's complex network environments, managing and troubleshooting devices can be a time-consuming and error-prone task. The Network AI Agent was created to address these challenges by providing a powerful, yet intuitive, solution for network automation. By leveraging the power of AI, this tool simplifies network management, reduces manual effort, and empowers network engineers to focus on more strategic initiatives.

## Features

- **AI-Powered Network Commands**: Use natural language to manage network devices.
- **Multi-Device Support**: Execute commands across multiple devices simultaneously.
- **Parallel Execution**: Efficiently process commands in parallel using `ThreadPoolExecutor`.
- **Structured Output**: Receive beautifully formatted output, especially for interface data, thanks to `tabulate`.
- **Workflow Management**: Manage complex network workflows with a state machine powered by `LangGraph`.
- **Secure Device Access**: Ensure secure device communication with SSH connectivity via `netmiko`.

## Getting Started

### Prerequisites

- Python 3.12 or higher
- `uv` package manager
- SSH access to your network devices
- A Groq API key for AI functionality

### Installation and Configuration

1. **Clone the repository and navigate to the project directory**:

```bash
git clone https://github.com/sydasif/network-automation-agent.git
cd network-agent
```

2. **Install the required dependencies**:

```bash
uv sync
```

3. **Configure your environment**:

```bash
cp .env.example .env
```

Then, add your Groq API key to the newly created `.env` file.

4. **Configure and Migrate Your Network Devices**:

The device inventory is now managed by a SQLite database (`inventory.db`) for improved performance and scalability. To populate it, follow this two-step process:

**Step 1: Configure `hosts.yaml`**

First, add your network device details to the `hosts.yaml` file. This file is used only for the initial data migration.

```yaml
devices:
  - name: sw1
    host: 192.168.121.101
    username: admin
    password_env_var: DEVICE_PASSWORD
    device_type: cisco_ios
  - name: sw2
    host: 192.168.121.102
    username: admin
    password_env_var: DEVICE_PASSWORD
    device_type: cisco_ios
```

**Step 2: Run the Migration Script**

Next, run the migration script to create the database and import the devices from your `hosts.yaml` file:

```bash
uv run hosts.py
```

This will create an `inventory.db` file. Once the migration is complete, the `hosts.yaml` file is no longer used for operations.

## API Documentation

### Main Components

#### 1. Application Entry Point (`main.py`)

Contains the interactive CLI interface for the network automation agent. The `chat_loop` function manages the conversation flow between the user and the agent in a continuous loop until the user exits.

#### 2. Graph Router (`graph/router.py`)

Implements a state graph using LangGraph with three main nodes:

- **Understand**: Parses user input and determines if tools need to be executed
- **Execute**: Runs network commands on specified devices
- **Respond**: Formats and returns results to the user

The workflow uses conditional routing based on whether the LLM has generated tool calls.

#### 3. Graph Nodes (`graph/nodes.py`)

Contains the three core node functions:

- `understand_node`: Analyzes conversation history and creates appropriate system messages
- `execute_node`: Processes LLM-generated tool calls and executes network commands
- `respond_node`: Synthesizes results and generates the final response to the user

#### 4. LLM Client (`llm/client.py`)

Provides a function to create and configure a ChatGroq LLM instance optimized for network automation tasks with deterministic responses.

#### 5. Command Execution Tool (`tools/commands.py`)

A LangChain tool that executes commands on network devices with:

- Parallel execution capabilities
- Support for single or multiple devices
- TextFSM parsing for structured output
- Comprehensive error handling

#### 6. Database Utilities (`utils/database.py`)

Contains SQLAlchemy models and utilities for managing device inventory in SQLite database including:

- `Device` model definition
- Database engine and session management
- Context manager for database sessions

#### 7. Device Utilities (`utils/devices.py`)

Provides utility functions for managing device configurations with caching:

- `get_device_by_name`: Retrieves a specific device from the database
- `get_all_device_names`: Retrieves all device names with caching
- `clear_device_cache`: Clears the device names cache

### Core Data Model

#### Device Model

The Device model has the following attributes:

- `id`: Unique identifier for the device record
- `name`: Unique name identifier for the device
- `host`: IP address or hostname of the network device
- `username`: Username for SSH authentication
- `password_env_var`: Name of environment variable containing the password
- `device_type`: Device type identifier for Netmiko (e.g., 'cisco_ios')

### Tool APIs

#### `run_command` Tool

```python
@tool
def run_command(device: Union[str, list[str]], command: str) -> str:
```

Executes a command on one or more network devices. Returns a JSON string containing:

- `command`: The command executed
- `summary`: Statistics about execution success/failure
- `devices`: Detailed results for each device

## Usage

To run the agent in interactive mode, use the following command:

```bash
uv run main.py
```

You can then enter commands in natural language, such as:

- "Show me the version of router-1"
- "Show interfaces on switch-1"
- "Show version on all devices"
- "Show running-config on router-1 and switch-1"

To exit the agent, simply type `quit`.

## Example Usage

Here's an example conversation showing how to interact with the Network AI Agent:

```markdown
🤖 Network AI Agent Ready!
Type 'quit' to exit.

You: Hi,

🤖 Agent: Hi there! 👋 How can I help you with your network today? If you have any device logs, command outputs, or specific questions, just let me know and I’ll break everything down for you.

You: check device version only for all devices

🤖 Agent: **Device Version Summary**

| Device | Software Image | Version | Release |
|--------|----------------|---------|---------|
| **sw1** | X86_64BI_LINUX_L2-ADVENTERPRISEK9-M | **17.15.1** | fc4 |
| **sw2** | X86_64BI_LINUX_L2-ADVENTERPRISEK9-M | **17.15.1** | fc4 |

*All devices report the same IOS‑XE version (17.15.1) and release (fc4).*

You: now check mgmt interface ip on both devices

🤖 Agent: **Management‑Interface IPs**

| Device | Likely Management Interface | IP Address |
|--------|-----------------------------|------------|
| **sw1** | Ethernet0/0 | **192.168.121.101** |
| **sw2** | Ethernet0/0 | **192.168.121.102** |

*Both switches have their Ethernet0/0 interfaces configured with the 192.168.121.x addresses, which are typically used for out‑of‑band management.*

You: Good, show me loopback intefaces on sw1

🤖 Agent: **Loopback0 – sw1**

| Attribute | Value |
|-----------|-------|
| **Interface** | Loopback0 |
| **Link status** | up |
| **Protocol status** | up |
| **IP address** | 10.0.0.1/32 |
| **MTU** | 1514 |
| **Bandwidth** | 8 000 000 Kbit |
| **Delay** | 5 000 µs |
| **Encapsulation** | LOOPBACK |
| **Last input / output** | never |
| **Input / output rates** | 0 bps |
| **Error counters** | all zero (input_errors, output_errors, etc.) |

*Loopback0 is fully operational with a single IPv4 address (10.0.0.1/32) and no traffic or error activity.*

You: check ospf summary on sw2

🤖 Agent: **OSPF Summary – sw2**

| Item | Detail |
|------|--------|
| **Process** | OSPF 1 |
| **Router ID** | 10.0.0.2 |
| **Start time** | 00:00:33.901 |
| **Uptime** | 00:25:35.698 |
| **Reference bandwidth** | 100 Mbps |
| **Areas** | 1 (BACKBONE 0.0.0.0) – 3 interfaces (Ethernet0/0, Ethernet0/1, Loopback0) |
| **LSA count** | 2 total (1 router‑LSA, 1 network‑LSA) |
| **External LSAs** | 0 |
| **Opaque AS LSAs** | 0 |
| **SPF executions** | 5 (last run 00:25:07.759 ago) |
| **Adjacency limits** | 300 (initial/maximum) |
| **Flood/LSA pacing** | Flood 33 ms, LSA throttle 50 ms, LSA group pacing 240 s |
| **Authentication** | None |
| **NSF helpers** | IETF & Cisco enabled |
| **Key flags** | Supports LLS, opaque LSAs, NSSA, DB‑exchange summary optimization; no area transit capability |

*The router is running OSPF with a single backbone area, no external routes, and a minimal LSA database. SPF has converged 5 times during the 25‑minute uptime.*

You: quit
Goodbye!
```

## Architecture

The agent is built on a `LangGraph`-based state machine with three main nodes:

1. **Understand**: Parses the user's intent to extract device names and commands.
2. **Execute**: Runs the network commands on the specified devices.
3. **Respond**: Formats and returns the results to the user.

```text
+-----------------+      +-----------------+      +-----------------+
|                 |      |                 |      |                 |
|   Understand    +---->     Execute     +---->     Respond     |
| (Parse Intent)  |      | (Run Commands)  |      | (Format Output) |
|                 |      |                 |      |                 |
+-----------------+      +-----------------+      +-----------------+
```

## Supported Commands

The agent can execute any command supported by your network devices, with special formatting for:

- `show version`
- `show interfaces`
- `show ip route`
- `show running-config`
- `show startup-config`

## Contributing

Contributions are welcome! If you'd like to contribute to this project, please follow these steps:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature/your-feature-name`).
3. Make your changes and commit them (`git commit -m 'Add some feature'`).
4. Push to the branch (`git push origin feature/your-feature-name`).
5. Open a pull request.

Please make sure to update tests as appropriate.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
