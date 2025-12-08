# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2025-12-08

### 🚀 Major Architecture Shift - Linear Pipeline

#### Changed

- **Workflow Architecture**: Migrated from Cyclic ReAct loop to **Linear Pipeline** (`Understanding` -> `Execute` -> `Response`).
- **Output Handling**: Implemented **Pydantic Structured Outputs** for strict, type-safe JSON generation.
- **Memory Management**: Replaced naive history slicing with **Smart Context Compression** in `core/context_manager.py`.
- **UI Formatting**: Standardized on **Markdown** summaries with tables and headers.

#### Removed

- **Planner Node**: Removed complex planning logic (`agent/nodes/planner_node.py`).
- **Multi-Command Tool**: Removed planning tool (`tools/multi_command.py`).
- **Response Tool**: Removed explicit response triggering (`tools/response_tool.py`).
- **Manual JSON Parsing**: Replaced regex-based parsing with `llm.with_structured_output`.

#### Fixed

- **Stability**: Fixed "Thinking out loud" crashes by removing the LLM's ability to loop back after execution.
- **Token Limits**: Fixed "Goldfish Memory" issues in long sessions using context compression.

---

## [2.0.0] - 2025-12-01

### 🎉 Major Refactoring - Class-Based Modular Architecture

#### Added

- **Core Infrastructure Package** (`core/`)
  - `NetworkAgentConfig` - Centralized configuration management
  - `NornirManager` - Nornir instance lifecycle management
  - `DeviceInventory` - Device information and validation
  - `TaskExecutor` - Network task execution with error handling
  - `LLMProvider` - LLM instance management and caching

- **Tools Package Refactoring** (`tools/`)
  - `NetworkTool` - Abstract base class for all tools
  - `ShowCommandTool` - Class-based show command implementation
  - `ConfigCommandTool` - Class-based config command implementation
  - `PlannerTool` - Complex task planning tool
  - `ResponseTool` - Final response tool
  - Tool registry pattern for dynamic tool loading

- **Agent Workflow Package** (`agent/`)
  - `NetworkAgentWorkflow` - Workflow orchestration manager
  - `AgentNode` - Abstract base class for workflow nodes
  - `UnderstandNode` - Input processing and output structuring
  - `ApprovalNode` - Human-in-the-loop approval
  - `ExecuteNode` - Tool execution wrapper
  - `PlannerNode` - Task planning node
  - `State` - Workflow state management

- **CLI Package** (`cli/`)
  - `NetworkAgentCLI` - Main application lifecycle manager
  - `CommandProcessor` - Command parsing and validation

- **UI Package** (`ui/`)
  - Moved `NetworkAgentUI` from `utils/` to dedicated package
  - Updated for new config system
  - Enhanced logging with custom handlers

- **Documentation**
  - Complete `README.md` rewrite with new architecture
  - New `docs/ARCHITECTURE.md` with detailed design docs
  - Mermaid diagrams for workflow and dependencies
  - Development guide and contribution guidelines

#### Changed

- **Architecture** - Complete migration from functional to class-based OOP design
- **Dependency Management** - Full dependency injection throughout
- **Code Organization** - Modular package structure with clear boundaries
- **Entry Point** - Simplified `main.py` (now 80 lines vs 221 lines)
- **Structured Output** - Manual JSON parsing to avoid Groq API compatibility issues
- **Type Hints** - Removed problematic Nornir type hints for compatibility

#### Fixed

- **Import Errors** - Fixed Nornir type import issues
- **Structured Output** - Resolved Groq API "json tool not found" error
- **Error Handling** - Improved network-specific error messages

#### Removed

- Old functional code moved to `.old_code_backup/`
  - `agent/nodes.py` → Replaced by `agent/nodes/` package
  - `agent/workflow.py` → Replaced by `agent/workflow_manager.py`
  - `agent/router.py` → Routing logic now in `NetworkAgentWorkflow`
  - `tools/show.py`, `tools/config.py`, etc. → Replaced by class-based tools
  - `utils/devices.py` → Split into core modules
  - `utils/ui.py` → Moved to `ui/console_ui.py`
  - `settings.py` → Replaced by `core/config.py`

### 📊 Statistics

- **26 new classes** created
- **10 old files** backed up
- **5 packages** fully modularized
- **100% class-based** architecture
- **Zero circular dependencies**

### 🧪 Testing

- All code passes `ruff` linting
- Import errors resolved
- Successful end-to-end testing with live devices
- Configuration change approval workflow verified

---

## [1.0.0] - 2024

### Initial Release

- Basic network automation with AI
- LangGraph workflow
- Nornir integration
- Show and config commands
- Human-in-the-loop approval
- Interactive and single command modes

[2.1.0]: https://github.com/sydasif/network-automation-agent/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/sydasif/network-automation-agent/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/sydasif/network-automation-agent/releases/tag/v1.0.0
