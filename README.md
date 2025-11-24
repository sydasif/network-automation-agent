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
# Default password for devices using the DEVICE_PASSWORD variable
DEVICE_PASSWORD=your_secure_password
```

**Create `hosts.yaml`:**

```yaml
devices:
  - name: sw1
    host: 192.168.1.10
    username: admin
    # Maps to the env var name defined in .env
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

**CLI Mode (Interactive):**

```bash
python main.py
```

**Single Command Mode:**

```bash
# Run a show command on a specific device
python main.py --device sw1 'show version'

# Run a configuration command (requires approval)
python main.py --device sw1 'interface eth0 shutdown'

# Run without specifying a device (not recommended)
python main.py 'show ip route'
```

---

## 🏗️ Architecture & Logic

The project follows a flattened, **KISS** architecture:

| File | Purpose |
| :--- | :--- |
| **`agent.py`** | The "Brain". Contains the LangGraph state machine, prompts, and LLM logic. |
| **`tools.py`** | The "Hands". Handles SSH connections (Netmiko) and LangChain tool definitions. |
| **`settings.py`** | Central configuration and path management. |
| **`app.py`** | Chainlit Web UI entry point. |
| **`main.py`** | Terminal CLI entry point. |

### The Workflow (ReAct Loop)

1. **Understand Node**: The LLM analyzes your request (e.g., "Check VLANs").
2. **Routing**:
    * *Read-Only (Show)*: Routes to **Execute**.
    * *Config (Change)*: Routes to **Approval** (Interrupts for human permission).
3. **Execute Node**: Runs the command via Netmiko.
4. **Loop**: The output is fed back to **Understand**, which formats the final answer.

### 🛡️ Security Features

* **Human Approval**: Any command that modifies configuration (`config_command`) requires explicit "Yes/Approve" from the user.
* **Env Vars**: Passwords are never stored in plain text in the inventory file.
* **Read-Only Default**: The agent prefers `show_command` unless explicitly asked to configure.
