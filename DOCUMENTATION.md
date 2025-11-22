# API Documentation

This document provides a detailed overview of the main components, data models, and tool APIs used in the Network AI Agent.

## Main Components

### 1. Application Entry Point (`main.py`)

Contains the interactive CLI interface for the network automation agent. The `chat_loop` function manages the conversation flow between the user and the agent in a continuous loop until the user exits.

### 2. Graph Router (`graph/router.py`)

Implements a state graph using LangGraph with three main nodes:

- **Understand**: Parses user input and determines if tools need to be executed.
- **Execute**: Runs network commands on specified devices.
- **Respond**: Formats and returns results to the user.

The workflow uses conditional routing based on whether the LLM has generated tool calls.

### 3. Graph Nodes (`graph/nodes.py`)

Contains the three core node functions:

- `understand_node`: Analyzes conversation history and creates appropriate system messages.
- `execute_node`: Processes LLM-generated tool calls and executes network commands.
- `respond_node`: Synthesizes results and generates the final response to the user.

### 4. LLM Client (`llm/client.py`)

Provides a function to create and configure a ChatGroq LLM instance optimized for network automation tasks with deterministic responses.

### 5. Command Execution Tool (`tools/commands.py`)

A LangChain tool that executes commands on network devices with:

- Parallel execution capabilities
- Support for single or multiple devices
- TextFSM parsing for structured output
- Comprehensive error handling

### 6. Database Utilities (`utils/database.py`)

Contains SQLAlchemy models and utilities for managing the device inventory in a SQLite database, including:

- `Device` model definition
- Database engine and session management
- Context manager for database sessions

### 7. Device Utilities (`utils/devices.py`)

Provides utility functions for managing device configurations with caching:

- `get_device_by_name`: Retrieves a specific device from the database.
- `get_all_device_names`: Retrieves all device names with caching.
- `clear_device_cache`: Clears the device names cache.

---

## Core Data Model

### Device Model

The `Device` model has the following attributes:

- `id`: Unique identifier for the device record.
- `name`: Unique name identifier for the device.
- `host`: IP address or hostname of the network device.
- `username`: Username for SSH authentication.
- `password_env_var`: Name of the environment variable containing the password.
- `device_type`: Device type identifier for Netmiko (e.g., 'cisco_ios').

---

## Tool APIs

### `run_command` Tool

```python
@tool
def run_command(device: Union[str, list[str]], command: str) -> str:
```

Executes a command on one or more network devices. It returns a JSON string containing:

- `command`: The command that was executed.
- `summary`: Statistics about execution success/failure.
- `devices`: Detailed results for each device.
