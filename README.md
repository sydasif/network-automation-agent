<div align="center">

<img src="https://github.com/sydasif/sydasif.github.io/blob/main/assets/img/favicons/favicon-96x96.png" alt="Network AI Agent Logo" width="120"/>

# Network AI Agent

**A powerful, AI-driven CLI tool for seamless network automation and management.**

<p>
    <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.12%2B-blue"></a>
    <a href="#"><img src="https://img.shields.io/badge/License-MIT-green"></a>
    <a href="https://github.com/sydasif/network-automation-agent"><img src="https://img.shields.io/badge/PRs-Welcome-brightgreen"></a>
</p>

</div>

A lightweight, "Human-in-the-Loop" AI agent that translates natural language into network configuration and show commands. Built with **LangGraph**, **Netmiko**, and **Chainlit**.

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
LLM_MODEL_NAME=openai/gpt-oss-20b
DEVICE_PASSWORD=your_secure_password
```

**Create `hosts.yaml`:**

```yaml
devices:
  - name: sw1
    host: 192.168.1.10
    username: admin
    password_env_var: DEVICE_PASSWORD
    device_type: cisco_ios

  - name: rtr1
    host: 192.168.1.1
    username: cisco
    password_env_var: DEVICE_PASSWORD
    device_type: cisco_xe
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
| **`tools/`** | The "Hands". Handles SSH connections (Netmiko) and robust command parsing. |
| **`app.py`** | Chainlit Web UI entry point. |
| **`main.py`** | Terminal CLI entry point. |

### Key Features

1. **Batching Support**: The agent can configure multiple devices in a single turn.
    * *User*: "Update NTP server on all switches."
    * *Agent*: Generates one approval request containing a list of all target devices.
2. **Safety First**:
    * Any `config_command` triggers a **Human-in-the-Loop** interrupt.
    * The Agent cannot execute changes without your explicit "Yes".
3. **Input Sanitization**:
    * Automatically cleans up messy LLM outputs (e.g., splitting newline-separated commands into proper lists) before sending to Netmiko.

### The Workflow

1. **Understand Node**: The LLM analyzes your request.
2. **Routing**:
    * *Read-Only*: Routes directly to **Execute**.
    * *Config*: Routes to **Approval** (Interrupts for human permission).
3. **Execute Node**: Runs the command via Netmiko.
4. **Loop**: Output is fed back to the LLM to format the final answer.
