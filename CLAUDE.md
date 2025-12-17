# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The Network Automation Agent is an AI-powered network automation assistant that uses natural language to manage network devices. Built with LangGraph, Groq (Llama 3.3), and Nornir, it features a linear pipeline architecture for safe and predictable network operations.

## Architecture

The system follows a linear pipeline architecture with four main nodes:

- **Understanding Node**: Analyzes user intent using structured LLM output and selects appropriate tools
- **Approval Node**: Intercepts configuration changes requiring human approval with risk assessment
- **Execute Node**: Runs Nornir tasks against network devices using Netmiko
- **Response Node**: Generates structured Markdown summaries using LLM formatting

The workflow is implemented using LangGraph with a deterministic "One-Shot" approach (Intent → Action → Summary) that prevents infinite loops and ensures predictable behavior for network operations.

## State Management

The system uses an extended state structure defined in `agent/state.py`:

- `State` contains a `messages` field that stores the conversation history
- `device_status`: Optional[Dict[str, Any]] - for tracking device status
- `current_session`: Optional[str] - for session management
- `approval_context`: Optional[Dict[str, Any]] - for approval context
- `execution_metadata`: Optional[Dict[str, Any]] - for execution metadata
- Messages flow between nodes and contain both user input and tool results
- The state uses LangGraph's `add_messages` reducer for automatic message updates
- Session persistence is handled via in-memory checkpointing

## Structured Output Schemas

The system relies on Pydantic schemas for structured LLM outputs (in `agent/schemas.py`):

- `ExecutionPlan`: Contains a list of `NetworkAction` steps to execute and an optional direct response
- `NetworkAction`: Represents a single action with `action_type` (read/configure), `device`, and `command`
- `AgentResponse`: Structured response with `summary` (Markdown), `structured_data`, and optional `error`

## Key Components

- `agent/`: Core AI logic including workflow, nodes, state management, and structured schemas
- `core/`: Infrastructure components like configuration, device connectivity, LLM provider, and message management
- `monitoring/`: Monitoring and observability components including tracing, callbacks, dashboard, and alerting
- `tools/`: Network operation capabilities (show and config commands) with validation and risk assessment
- `cli/`: Command-line interface and orchestration
- `ui/`: Terminal user interface with rich console output and approval prompts
- `utils/`: Utility functions and logging

## Configuration and Setup

### Environment Variables
- `GROQ_API_KEY`: API key for Groq LLM service
- `NUM_WORKERS`: Number of parallel workers (default: 20)
- `NETMIKO_TIMEOUT`: Command timeout in seconds (default: 30)
- `NETMIKO_CONN_TIMEOUT`: Connection timeout in seconds (default: 10)
- `NETMIKO_SESSION_TIMEOUT`: Session timeout in seconds (default: 60)
- `NETMIKO_KEEP_ALIVE`: Seconds to keep connection alive (default: 30)

### Device Inventory
- `hosts.yaml`: Defines individual network devices with hostname and group membership
- `groups.yaml`: Defines device groups with platform-specific settings (username, password, platform)
- Supported platforms include `cisco_ios`, `arista_eos`, and other Netmiko-compatible platforms

## Approval and Risk Assessment

The system includes sophisticated approval mechanisms:

- Configuration commands automatically trigger approval requests with risk assessment
- Risk levels (high/medium/low) are determined by keyword analysis
- High-risk keywords include: "no ", "shutdown", "delete", "clear", "reload", "erase"
- Medium-risk keywords include: "ip address", "route", "acl", "access-list"
- Users must explicitly approve configuration changes before execution
- Show commands bypass approval and execute directly after validation

## Development Commands

### Running the Application

- Interactive chat mode: `uv run python main.py --chat`
- Single command mode: `uv run python main.py "show ip interface brief on R1"`
- Debug mode: `uv run python main.py --chat --debug`
- Monitoring dashboard: `uv run python main.py --monitor`

### Testing

- Run all tests: `uv run pytest`
- Run specific test file: `uv run pytest tests/unit/test_core/test_config.py`
- Run specific test: `uv run pytest tests/unit/test_core/test_config.py::test_function_name`
- Run tests with verbose output: `uv run pytest -v`

### Dependencies

- Install dependencies: `uv sync`
- Add new dependency: `uv add package_name`
- Update dependencies: `uv sync --refresh`

## Important Files

- `main.py` - Entry point of the application
- `agent/workflow_manager.py` - Defines the linear graph workflow with conditional routing
- `agent/nodes.py` - Contains all workflow nodes (understanding, approval, execute, response)
- `agent/schemas.py` - Pydantic schemas for structured LLM outputs (ExecutionPlan, AgentResponse)
- `agent/state.py` - State structure definition for the LangGraph workflow
- `core/nornir_manager.py` - Handles device connectivity and Nornir lifecycle
- `core/llm_provider.py` - LLM interface with Groq API
- `monitoring/tracing.py` - LangSmith tracing integration
- `monitoring/callbacks.py` - Custom monitoring callbacks for tracking execution
- `monitoring/dashboard.py` - Monitoring dashboard functionality
- `monitoring/alerting.py` - Alert management system
- `tools/show_tool.py` and `tools/config_tool.py` - Core network operation tools with validation
- `tools/validators.py` - Command validation and safety checks
- `config.yaml` - Nornir configuration
- `hosts.yaml` and `groups.yaml` - Device inventory configuration

## Safety and Validation

The system includes multiple layers of validation and safety:

- Device inventory validation to ensure target devices exist
- Command validation to prevent dangerous operations
- Human-in-the-loop approval for configuration changes
- Risk assessment for configuration commands based on keywords
- Structured output enforcement using Pydantic schemas
- Multi-level validation (syntax, semantics, device inventory)
- Prevention of destructive operations through show/config tool separation

## Working with Network Operations

- Show commands are executed directly after validation
- Configuration commands require explicit user approval with risk assessment
- Commands are validated against device inventory before execution
- The system supports multi-vendor network devices through Netmiko/Nornir
- Commands are parsed using structured LLM output to identify device targets and actions
- Results are formatted using structured LLM output for consistent presentation
