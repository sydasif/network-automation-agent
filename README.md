# Network Automation Agent 🤖

An AI-powered network automation assistant that uses natural language to manage network devices. Built with LangGraph, Groq LLM, and Nornir.

## ✨ Features

- **Natural Language Interface**: Describe what you want in plain English
- **Multi-Device Support**: Execute commands across multiple devices simultaneously
- **Human-in-the-Loop**: Configuration changes require approval before execution
- **Structured Output**: Clean JSON and Markdown formatted results
- **Interactive Chat**: Conversational interface for network operations
- **Plugin Architecture**: Easily add new tools and capabilities

## 🏗️ Architecture

The application follows a **modular, class-based architecture** with clear separation of concerns:

```text
┌─────────────────────────────────────────────────┐
│                   main.py                       │
│            (CLI Entry Point)                    │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│              cli/                               │
│  • NetworkAgentCLI (Application Lifecycle)      │
│  • CommandProcessor (Parsing & Validation)      │
└──────────────────┬──────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
┌───────▼────────┐    ┌──────▼──────┐
│   agent/       │    │    ui/      │
│ • Workflow     │    │ • Console   │
│ • Nodes        │    │ • Logging   │
└───────┬────────┘    └─────────────┘
        │
   ┌────┴────┐
   │         │
┌──▼──┐  ┌──▼────┐
│tools│  │ core/ │
│     │  │       │
└─────┘  └───────┘
```

### Package Structure

- **`core/`** - Infrastructure (Config, Nornir, Device Inventory, Task Executor, LLM Provider)
- **`tools/`** - Network automation tools (Show, Config, Plan, Response)
- **`agent/`** - LangGraph workflow and node implementations
- **`cli/`** - Application lifecycle and command processing
- **`ui/`** - Console UI and logging

### Key Classes

**Core Infrastructure:**

- `NetworkAgentConfig` - Centralized configuration management
- `NornirManager` - Nornir instance lifecycle
- `DeviceInventory` - Device information and validation
- `TaskExecutor` - Network task execution with error handling
- `LLMProvider` - LLM instance management

**Agent Workflow:**

- `NetworkAgentWorkflow` - Workflow orchestration
- `ContextManagerNode` - Conversation history management
- `UnderstandingNode` - Input processing & tool selection
- `ValidationNode` - Input validation and device verification
- `ApprovalNode` - Human-in-the-loop approval
- `ExecuteNode` - Tool execution
- `PlannerNode` - Complex task planning
- `FormatNode` - Structured output formatting

**Tools:**

- `ShowCommandTool` - Read-only show commands
- `ConfigCommandTool` - Configuration changes
- `MultiCommandTool` - Task planning
- `ResponseTool` - Final responses
- `FormatOutputTool` - Structured output formatting

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- `uv` package manager
- Network devices with SSH access
- Groq API key

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd network-automation-agent

# Install dependencies
uv sync

# Set up environment
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### Configuration

1. **Environment Variables** (`.env`):

```bash
GROQ_API_KEY=your_groq_api_key_here
```

2. **Nornir Configuration** (`config.yaml`):

```yaml
inventory:
  plugin: SimpleInventory
  options:
    host_file: "hosts.yaml"
    group_file: "groups.yaml"
runner:
  plugin: threaded
  options:
    num_workers: 20
logging:
  enabled: false
defaults:
  connection_options:
    netmiko:
      extras:
        timeout: 30
        conn_timeout: 10
        session_timeout: 60
```

3. **Device Inventory** (`hosts.yaml`):

```yaml
R1:
  hostname: 192.168.121.101
  groups: [arista]
sw1:
  hostname: 192.168.121.102
  groups: [cisco]
sw2:
  hostname: 192.168.121.103
  groups: [cisco]
```

4. **Groups Inventory** (`groups.yaml`):

```yaml
cisco:
  platform: cisco_ios
  username: admin
  password: admin

arista:
  platform: arista_eos
  username: admin
  password: admin
```

## 💻 Usage

### Single Command Mode

Execute a single command:

```bash
uv run python main.py "show version on R1"
```

With device specified:

```bash
uv run python main.py "show ip interface brief" --device R1
```

### Interactive Chat Mode

Start an interactive session:

```bash
uv run python main.py --chat
```

Example conversation:

```terminal
User > show version on R1
[Structured output with device details]

User > add loopback9 with ip 9.9.9.9/32 on R1
[Approval prompt for configuration change]
Proceed? (yes/no): yes
[Configuration applied successfully]
```

### Debug Mode

Enable detailed logging:

```bash
uv run python main.py --debug --chat
```

## 🔧 Development

### Project Structure

```bash
network-automation-agent/
├── main.py                 # Entry point
├── core/                   # Core infrastructure
│   ├── config.py
│   ├── nornir_manager.py
│   ├── device_inventory.py
│   ├── task_executor.py
│   └── llm_provider.py
├── tools/                  # Network tools
│   ├── base_tool.py
│   ├── show_tool.py
│   ├── config_tool.py
│   ├── plan_tool.py
│   └── response_tool.py
├── agent/                  # Workflow & nodes
│   ├── workflow_manager.py
│   ├── state.py
│   └── nodes/
│       ├── base_node.py
│       ├── context_manager_node.py
│       ├── understanding_node.py
│       ├── validation_node.py
│       ├── approval_node.py
│       ├── planner_node.py
│       ├── execute_node.py
│       └── format_node.py
├── cli/                    # CLI application
│   ├── application.py
│   └── command_processor.py
├── ui/                     # User interface
│   └── console_ui.py
├── utils/                  # Utilities
│   ├── logger.py
│   └── responses.py
└── tests/                  # Test suite
    ├── unit/
    └── integration/
```

### Adding a New Tool

1. Create a new tool class in `tools/`:

```python
from tools.base_tool import NetworkTool

class MyCustomTool(NetworkTool):
    @property
    def name(self) -> str:
        return "my_custom_tool"

    @property
    def description(self) -> str:
        return "Description of what the tool does"

    @property
    def args_schema(self) -> type[BaseModel]:
        return MyCustomInput

    def _execute_impl(self, **kwargs) -> str:
        # Implementation here
        pass
```

2. Register in `tools/__init__.py`:

```python
from tools.my_custom_tool import MyCustomTool

def get_all_tools(task_executor: TaskExecutor) -> list:
    tools = [
        ShowCommandTool(task_executor),
        ConfigCommandTool(task_executor),
        MyCustomTool(task_executor),  # Add here
        # ...
    ]
    return [tool.to_langchain_tool() for tool in tools]
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=. --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_core/test_config.py
```

### Code Quality

```bash
# Lint and format
uv run ruff check . --fix
uv run ruff format .

# Type checking
uv run mypy .
```

## 📚 Key Concepts

### Dependency Injection

All classes receive their dependencies via constructors:

```python
# In NetworkAgentCLI
self._nornir_manager = NornirManager(config)
self._device_inventory = DeviceInventory(self._nornir_manager)
self._task_executor = TaskExecutor(self._nornir_manager)
```

### Plugin Architecture

Tools are discovered and loaded through the registry:

```python
tools = get_all_tools(task_executor)  # All tools loaded dynamically
```

### LangGraph Workflow

The agent uses LangGraph for workflow orchestration:

1. **Context Manager** - Manage conversation history and context window
2. **Understanding** - Process input and select appropriate tools
3. **Validation** - Validate tool calls and device names
4. **Approval** - Request human approval for config changes
5. **Execute** - Run the tools
6. **Plan** - Break down complex tasks
7. **Format** - Structure tool outputs into JSON/Markdown

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Ensure tests pass and code is linted
5. Submit a pull request

## 📝 License

[Your License Here]

## 🙏 Acknowledgments

- **LangGraph** - Workflow orchestration
- **Groq** - Fast LLM inference
- **Nornir** - Network automation framework
- **Netmiko** - Multi-vendor SSH library

## 📞 Support

For issues and questions, please open an issue on GitHub.

---

**Made with ❤️ for Network Engineers**
