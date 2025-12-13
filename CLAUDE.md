# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The Network Automation Agent is an AI-powered network automation assistant that uses natural language to manage network devices. Built with LangGraph, Groq (Llama 3.3), and Nornir, it features a linear pipeline architecture for safe and predictable network operations.

## Architecture

The system follows a linear pipeline architecture with four main nodes:

- **Understanding Node**: Analyzes user intent and selects appropriate tools
- **Approval Node**: Intercepts configuration changes requiring human approval
- **Execute Node**: Runs Nornir tasks against network devices
- **Response Node**: Generates structured Markdown summaries

The workflow is implemented using LangGraph with a deterministic "One-Shot" approach (Intent → Action → Summary) that prevents infinite loops and ensures predictable behavior for network operations.

## Key Components

- `agent/`: Core AI logic including workflow, nodes, and state management
- `core/`: Infrastructure components like configuration, device connectivity, and message management
- `tools/`: Network operation capabilities (show and config commands) with validation
- `cli/`: Command-line interface and orchestration
- `ui/`: Terminal user interface
- `utils/`: Utility functions and logging

## Development Commands

### Running the Application

- Interactive chat mode: `uv run python main.py --chat`
- Single command mode: `uv run python main.py "show ip interface brief on R1"`
- Debug mode: `uv run python main.py --chat --debug`

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
- `agent/workflow_manager.py` - Defines the linear graph workflow
- `agent/nodes.py` - Contains all workflow nodes (understanding, approval, execute, response)
- `core/nornir_manager.py` - Handles device connectivity
- `tools/show_tool.py` and `tools/config_tool.py` - Core network operation tools with validation
- `agent/schemas.py` - Pydantic schemas for structured LLM outputs
- `config.yaml` - Application configuration
- `hosts.yaml` and `groups.yaml` - Device inventory

## Safety and Validation

The system includes multiple layers of validation and safety:

- Device inventory validation to ensure target devices exist
- Command validation to prevent dangerous operations
- Human-in-the-loop approval for configuration changes
- Risk assessment for configuration commands based on keywords
- Structured output enforcement using Pydantic schemas

## Working with Network Operations

- Show commands are executed directly after validation
- Configuration commands require explicit user approval
- Commands are validated against device inventory before execution
- The system supports multi-vendor network devices through Netmiko/Nornir
