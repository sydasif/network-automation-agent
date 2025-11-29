<div align="center">

<img src="https://github.com/sydasif/sydasif.github.io/blob/main/assets/img/favicons/favicon-96x96.png" alt="Network AI Agent Logo" width="120"/>

# Network AI Agent

**A powerful, AI-driven tool for seamless network automation and management.**

<p>
    <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.12%2B-blue"></a>
    <a href="#"><img src="https://img.shields.io/badge/License-MIT-green"></a>
    <a href="https://nornir.tech/"><img src="https://img.shields.io/badge/Powered%20By-Nornir-blueviolet"></a>
    <a href="https://www.docker.com/"><img src="https://img.shields.io/badge/Docker-Ready-blue"></a>
</p>

</div>

A lightweight, "Human-in-the-Loop" AI agent that translates natural language into network configuration and show commands. Built with **LangGraph**, **Nornir**, and **Rich**.

## 🚀 Quick Start (Docker)

The easiest way to run the agent is using Docker. This ensures a consistent environment.

### 1. Setup

```bash
git clone https://github.com/yourusername/network-agent.git
cd network-agent
```

### 2. Configuration

Create your secrets and inventory files.

**`.env`** (Secrets):

```ini
GROQ_API_KEY=gsk_your_api_key_here
```

**`hosts.yaml`** (Inventory):

```yaml
---
sw1:
  hostname: 192.168.1.10
  groups: [cisco]
sw2:
  hostname: 192.168.1.11
  groups: [cisco]
```

**`groups.yaml`** (Platform Definitions):

```yaml
---
cisco:
  platform: cisco_ios
  username: admin
  password: admin

arista:
  platform: arista_eos
  username: admin
  password: admin
```

### 3. Run

```bash
docker compose up --build
```

---

## 🐳 Docker Usage

The agent now runs in CLI mode only with both single command and interactive chat capabilities. Here are the ways to use it:

### Option 1: Run a single command

```bash
docker compose run --rm network-agent-cli python main.py "show ip interface brief"
```

### Option 2: Interactive chat mode (recommended)

```bash
# Start an interactive chat session
docker compose run --rm -it network-agent-cli python main.py --chat

# Or with a specific device
docker compose run --rm -it network-agent-cli python main.py --chat --device sw1
```

### Option 3: Start the container and run commands interactively

```bash
# Start the container in detached mode
docker compose up -d

# Execute a single command in the running container
docker compose exec network-agent-cli python main.py "show version on device1"

# Start an interactive chat session in the running container
docker compose exec -it network-agent-cli python main.py --chat

# For interactive shell access
docker compose exec -it network-agent-cli bash
# Then run: python main.py --chat  (for chat mode)
# Or run: python main.py "your command here"  (for single command)
```

### Option 4: Interactive shell session

```bash
docker compose run --rm -it network-agent-cli bash
# Then run your commands inside the container
```

---

## 🏗️ Architecture

The project follows a flattened, **KISS** architecture leveraging **Nornir** for parallel execution:

| Component | File | Purpose |
| :--- | :--- | :--- |
| **Brain** | `agent/` | LangGraph workflow, prompts, and decision routing. |
| **Hands** | `tools/` | Split into `show.py` (Read) and `config.py` (Write). |
| **Engine** | `utils/devices.py` | **Nornir** initialization and task execution engine. |
| **CLI** | `main.py` | Terminal entry point. |

### Key Features

1. **Parallel Execution**:
    * Uses **Nornir** to execute read-only commands (`show version`) on hundreds of devices simultaneously.
2. **Safety First**:
    * **Sequential Configs**: Configuration changes are handled sequentially with a **Human-in-the-Loop** approval step for every batch.
    * The Agent cannot execute changes without your explicit "Yes".
3. **Smart Input Sanitization**:
    * Automatically cleans up LLM outputs (e.g., stripping markdown code blocks from config sets) before sending to devices.
4. **Intelligent Structured Output**:
    * Uses **LangGraph's `with_structured_output`** to parse raw CLI output into structured JSON with human-readable summaries.
    * The LLM analyzes device responses and generates:
        * **Executive Summary**: Markdown-formatted insights highlighting operational status, health, and anomalies.
        * **Structured Data**: Parsed JSON output (dict/list) for programmatic access.
        * **Error Detection**: Automatically identifies and reports issues in device output.
    * Output is beautifully rendered in the console using **Rich** with proper JSON formatting and Markdown rendering.

---

## 🛠️ Local Development

If you prefer running without Docker:

1. **Install Dependencies**:

    ```bash
    # Using uv (Recommended)
    uv sync
    # Or standard pip
    pip install -r requirements.txt
    ```

2. **Run CLI**:

    ```bash
    python main.py "Show ip int brief on sw1"
    ```

---

## 📚 Tools & Modules

* **`agent.nodes`**: Defines the graph state, interaction logic, and structured output processing using Pydantic models.
* **`agent.workflow`**: Assembles the LangGraph workflow with approval routing and execution flow.
* **`utils.devices`**: Lazy-loads Nornir and injects secrets from environment variables.
* **`utils.ui`**: Rich-based UI components for beautiful console output with JSON and Markdown rendering.
* **`tools.show`**: Wraps `nornir_netmiko.netmiko_send_command`.
* **`tools.config`**: Wraps `nornir_netmiko.netmiko_send_config`.

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
