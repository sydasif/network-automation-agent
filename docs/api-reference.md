# API Documentation

This document provides detailed information about the main modules and classes in the Network Automation Agent.

## Table of Contents
- [Agent Module](#agent-module)
- [Core Module](#core-module)
- [Tools Module](#tools-module)
- [CLI Module](#cli-module)
- [UI Module](#ui-module)
- [Utilities](#utilities)

## Agent Module

The agent module contains the core AI logic and workflow management.

### NetworkAgentWorkflow

Located in `agent/workflow_manager.py`

The `NetworkAgentWorkflow` class manages the LangGraph workflow that powers the agent's decision-making process.

#### Constructor
```python
def __init__(
    self,
    llm_provider: LLMProvider,
    device_inventory: DeviceInventory,
    task_executor: TaskExecutor,
    tools: list,
    max_history_tokens: int = 3500,
)
```

**Parameters:**
- `llm_provider`: Provides access to the LLM service (Groq)
- `device_inventory`: Validates device existence and properties
- `task_executor`: Executes network tasks via Nornir
- `tools`: List of available network operation tools
- `max_history_tokens`: Maximum tokens for conversation history (default: 3500)

#### Methods

**build()**
- Creates and returns the LangGraph workflow
- Sets up the linear pipeline: Understanding → Approval/Execute → Response

**create_session_config(session_id)**
- Creates configuration for a specific session
- Returns a dict with thread_id for persistence

**get_approval_request(snapshot)**
- Extracts approval request from workflow state
- Returns tool calls that require approval

### Node Functions

Located in `agent/nodes.py`

#### understanding_node
- Analyzes user input and selects appropriate tools
- Validates command against device inventory
- Routes to approval for config commands, execute for show commands

#### approval_node
- Handles human-in-the-loop approval process
- Pauses workflow for user confirmation
- Routes to execute if approved, response if denied

#### execute_node
- Executes selected tools against network devices
- Handles both show and config commands
- Returns raw execution results

#### response_node
- Generates structured responses using LLM
- Formats results as Markdown summaries
- Uses Pydantic schemas for consistency

### State Management

Located in `agent/state.py`

The state management follows LangGraph patterns with the following nodes:
- `NODE_UNDERSTANDING`: Initial processing
- `NODE_APPROVAL`: Human approval step
- `NODE_EXECUTE`: Command execution
- `NODE_RESPONSE`: Response generation

## Core Module

The core module handles configuration, device connectivity, and task execution.

### NetworkAgentConfig

Located in `core/config.py`

Manages application configuration and validation.

#### Methods
**load()**
- Loads configuration from config.yaml
- Returns a NetworkAgentConfig instance

**validate()**
- Validates configuration settings
- Checks for required settings and valid values

### DeviceInventory

Located in `core/device_inventory.py`

Manages network device inventory and validation.

#### Methods
**load()**
- Loads device inventory from hosts.yaml and groups.yaml
- Returns a DeviceInventory instance

**validate_device(device_name)**
- Validates if a device exists in inventory
- Returns device information or raises exception

**get_device_info(device_name)**
- Retrieves detailed information about a device

### NornirManager

Located in `core/nornir_manager.py`

Manages Nornir instances for network automation tasks.

#### Methods
**get_instance()**
- Returns a configured Nornir instance
- Handles inventory loading and configuration

**cleanup()**
- Cleans up Nornir resources

### TaskExecutor

Located in `core/task_executor.py`

Executes network tasks using Nornir.

#### Methods
**execute_task(self, task_func, **kwargs)**
- Executes a Nornir task across target devices
- Handles task results and error reporting

### LLMProvider

Located in `core/llm_provider.py`

Manages access to the LLM service (Groq).

#### Methods
**get_llm()**
- Returns a configured LLM instance
- Handles API key and model configuration

## Tools Module

The tools module contains the network operation capabilities.

### ShowTool

Located in `tools/show_tool.py`

Handles read-only network commands.

#### Methods
**run(command: str, devices: list)**
- Executes show commands on specified devices
- Returns command output
- Validates commands before execution

### ConfigTool

Located in `tools/config_tool.py`

Handles configuration changes on network devices.

#### Methods
**run(commands: list, devices: list)**
- Executes configuration commands on specified devices
- Requires approval before execution
- Validates commands for safety

### Tool Registry

Located in `tools/registry.py`

Manages registration and access to available tools.

#### Methods
**register_tool(name, tool)**
- Registers a new tool with the system

**get_tool(name)**
- Retrieves a registered tool by name

**get_all_tools()**
- Returns all available tools

### Validators

Located in `tools/validators.py`

Contains validation functions for commands and devices.

#### Methods
**validate_device_exists(device_name, inventory)**
- Validates that a device exists in inventory

**validate_command_safety(command)**
- Checks if a command is safe to execute

**validate_command_syntax(command, device_platform)**
- Validates command syntax for specific device platform

## CLI Module

The CLI module handles user interaction and application orchestration.

### NetworkAgentCLI

Located in `cli/application.py`

Main CLI application class that coordinates all components.

#### Constructor
```python
def __init__(self, config: NetworkAgentConfig)
```

#### Methods
**run_interactive_chat(device=None)**
- Starts interactive chat mode
- Handles user input and agent responses

**run_single_command(command, device=None)**
- Executes a single command
- Returns the result

**cleanup()**
- Cleans up resources before exit

### Orchestrator

Located in `cli/orchestrator.py`

Manages the coordination between different system components.

#### Methods
**initialize_components()**
- Initializes all required components
- Sets up dependencies

**execute_workflow(input_data)**
- Executes the main workflow
- Coordinates between nodes

### Bootstrapper

Located in `cli/bootstrapper.py`

Handles application initialization and dependency setup.

#### Methods
**bootstrap()**
- Initializes the application
- Sets up configuration and components

## UI Module

The UI module provides the terminal user interface.

### ConsoleUI

Located in `ui/console_ui.py`

Provides rich terminal interface using prompt-toolkit.

#### Methods
**display_message(message)**
- Displays a message to the user
- Handles formatting and styling

**get_user_input(prompt)**
- Gets input from the user
- Handles command history and completion

**display_results(results)**
- Displays command results
- Formats output for readability

## Utilities

Utility functions used throughout the application.

### Logger

Located in `utils/logger.py`

Handles application logging.

#### Methods
**setup_logging(level=logging.INFO)**
- Sets up file-based logging
- Configures log format and level

### Responses

Located in `utils/responses.py`

Helper functions for response formatting.

#### Methods
**format_show_result(result)**
- Formats show command results
- Creates readable output

**format_config_result(result)**
- Formats configuration command results
- Includes success/failure information

## Main Entry Point

Located in `main.py`

The main entry point provides the command-line interface for the application.

### main() function
- Parses command-line arguments
- Sets up logging
- Initializes configuration
- Creates and runs the CLI application
- Handles cleanup and error conditions

## Configuration Files

### config.yaml
- Nornir configuration
- Inventory settings
- Runner configuration
- Connection timeouts
- Logging settings

### hosts.yaml
- Individual device definitions
- Hostname/IP mapping
- Group memberships
- Device-specific settings

### groups.yaml
- Device group definitions
- Platform specifications
- Authentication credentials
- Connection parameters