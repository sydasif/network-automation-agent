# Network AI Agent

<div align="center">

<img src="https://github.com/sydasif/sydasif.github.io/blob/main/assets/img/favicons/favicon-96x96.png" alt="Network AI Agent Logo" width="120"/>

**A powerful, AI-driven CLI tool for seamless network automation and management.**

<p>
    <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.12%2B-blue"></a>
    <a href="#"><img src="https://img.shields.io/badge/License-MIT-green"></a>
    <a href="https://github.com/sydasif/network-automation-agent"><img src="https://img.shields.io/badge/PRs-Welcome-brightgreen"></a>
</p>

</div>

A lightweight, "Human-in-the-Loop" AI agent that translates natural language into network configuration and show commands. Built with **LangGraph**, **Nornir**, **Netmiko**, and **Chainlit**.

## ⚡ Quick Start

### 1. Installation

Requires Python 3.12+.

```bash
git clone https://github.com/yourusername/network-agent.git
cd network-agent
uv sync  # Or: pip install -r requirements.txt
```

### 2. Configuration

The agent requires two files in the root directory: `.env` (secrets) and `hosts.yaml` (inventory).

**Create `.env`:**

```ini
GROQ_API_KEY=gsk_your_api_key_here
LLM_MODEL_NAME=llama3-70b-8192  # or another supported model
DEVICE_PASSWORD=your_secure_password
```

**Create `hosts.yaml`:**

```yaml
---
sw1:
  hostname: 192.168.121.102
  groups: [cisco]
  data:
    password_env_var: DEVICE_PASSWORD
sw2:
  hostname: 192.168.121.103
  groups: [cisco]
  data:
    password_env_var: DEVICE_PASSWORD
r1:
  hostname: 192.168.121.101
  groups: [arista]
  data:
    password_env_var: DEVICE_PASSWORD
```

**Create `groups.yaml`:**

```yaml
---
cisco:
  platform: cisco_ios
  username: admin
arista:
  platform: arista_eos
  username: admin
```

### 3. Usage

**Web Interface (Recommended):**

```bash
chainlit run app.py -w
```

**CLI Mode:**

```bash
# Interactive mode
python main.py

# Single Command (Supports Natural Language)
python main.py "Show ip int brief on sw1"

# Batch Configuration (Smart & Safe)
python main.py "Create vlan 10 named 'Data' on sw1 and rtr1"
```

---

## 🏗️ Architecture & Logic

The project follows a flattened, **KISS** architecture:

| File | Purpose |
| :--- | :--- |
| **`agent/`** | The "Brain". Contains the LangGraph state machine, prompts, and router. |
| **`tools/`** | The "Hands". Handles SSH connections (Nornir/Netmiko) and robust command parsing. |
| **`utils/devices.py`** | Device inventory management and connection handling. |
| **`app.py`** | Chainlit Web UI entry point. |
| **`main.py`** | Terminal CLI entry point. |
| **`settings.py`** | Configuration settings for the application. |

### Key Features

1. **Batching Support**: The agent can configure multiple devices in a single turn.
    * *User*: "Update NTP server on all switches."
    * *Agent*: Generates one approval request containing a list of all target devices.
2. **Safety First**:
    * Any `config_command` triggers a **Human-in-the-Loop** interrupt.
    * The Agent cannot execute changes without your explicit "Yes".
3. **Input Sanitization**:
    * Automatically cleans up messy LLM outputs (e.g., splitting newline-separated commands into proper lists) before sending to Netmiko.
4. **Structured Output**:
    * Uses TextFSM to parse `show` command output into structured JSON.

### The Workflow

1. **Understand Node**: The LLM analyzes your request.
2. **Routing**:
    * *Read-Only*: Routes directly to **Execute**.
    * *Config*: Routes to **Approval** (Interrupts for human permission).
3. **Execute Node**: Runs the command via Nornir/Netmiko.
4. **Loop**: Output is fed back to the LLM to format the final answer.

---

## 📚 API Documentation

### Modules

* **`agent.nodes`**: Defines the graph state, constants, and node logic for the LangGraph workflow
* **`agent.router`**: Contains routing logic for conditional edges in the workflow
* **`agent.workflow`**: Assembles the complete LangGraph workflow
* **`tools.show`**: Network tools for read-only 'show' commands.
* **`tools.config`**: Network tools for configuration commands.
* **`utils.devices`**: Handles device inventory loading and connection management
* **`settings`**: Contains configuration settings for the application
* **`app`**: Chainlit web interface entry point
* **`main`**: CLI entry point

### Key Functions

* `run_single_command()`: Execute a single network command through the agent workflow
* `create_graph()`: Creates and compiles the LangGraph workflow
* `show_command()`: Execute read-only 'show' commands on network devices
* `config_command()`: Apply configuration changes to network devices
* `execute_nornir_task()`: Wrapper for executing Nornir tasks.

---

## 🛠️ Development

### Project Setup

To set up the development environment:

```bash
# Clone the repository
git clone https://github.com/yourusername/network-agent.git
cd network-agent

# Install dependencies
uv sync  # or pip install -r requirements.txt

# Create virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync
```

### Running Tests

Currently, there are no automated tests in the project. To manually test functionality:

1. Start the web interface: `chainlit run app.py -w`
2. Or test the CLI: `python main.py "show version on sw1"`

### Code Formatting

The project uses Ruff for linting and formatting:

```bash
# Run linter and auto-fix issues
ruff check --fix .

# Format code
ruff format .
```

---

## 🚀 Deployment

### Prerequisites

* Python 3.12+
* `uv` package manager or `pip`
* Network device access (SSH)

### Production Deployment

1. Clone the repository to your server
2. Set up the virtual environment
3. Configure the `.env` and `hosts.yaml` files appropriately
4. Run the application using a process manager like systemd, pm2, or similar

For web deployment, consider using a WSGI server like Gunicorn with a reverse proxy like Nginx.
