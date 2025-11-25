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

A lightweight, "Human-in-the-Loop" AI agent that translates natural language into network configuration and show commands. Built with **LangGraph**, **Nornir**, and **Chainlit**.

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
LLM_MODEL_NAME=llama-3.3-70b-versatile
DEVICE_PASSWORD=your_secure_password
```

**`hosts.yaml`** (Inventory):

```yaml
---
sw1:
  hostname: 192.168.1.10
  groups: [cisco]
  data:
    password_env_var: DEVICE_PASSWORD
sw2:
  hostname: 192.168.1.11
  groups: [cisco]
  data:
    password_env_var: DEVICE_PASSWORD
```

**`groups.yaml`** (Platform Definitions):

```yaml
---
cisco:
  platform: cisco_ios
  username: admin
  connection_options:
    netmiko:
      extras:
        secret: "" # Optional enable password
```

### 3. Run

```bash
docker compose up --build
```

Access the Web UI at **<http://localhost:8000>**

---

## 🏗️ Architecture

The project follows a flattened, **KISS** architecture leveraging **Nornir** for parallel execution:

| Component | File | Purpose |
| :--- | :--- | :--- |
| **Brain** | `agent/` | LangGraph workflow, prompts, and decision routing. |
| **Hands** | `tools/` | Split into `show.py` (Read) and `config.py` (Write). |
| **Engine** | `utils/devices.py` | **Nornir** initialization and task execution engine. |
| **UI** | `app.py` | Chainlit Web Interface. |
| **CLI** | `main.py` | Terminal entry point. |

### Key Features

1. **Parallel Execution**:
    * Uses **Nornir** to execute read-only commands (`show version`) on hundreds of devices simultaneously.
2. **Safety First**:
    * **Sequential Configs**: Configuration changes are handled sequentially with a **Human-in-the-Loop** approval step for every batch.
    * The Agent cannot execute changes without your explicit "Yes".
3. **Smart Input Sanitization**:
    * Automatically cleans up LLM outputs (e.g., stripping markdown code blocks from config sets) before sending to devices.
4. **Structured Output**:
    * Uses **TextFSM** (via `ntc-templates`) to parse raw CLI output into structured JSON data for the LLM.

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

2. **Run Web UI**:

    ```bash
    chainlit run app.py -w
    ```

3. **Run CLI**:

    ```bash
    python main.py "Show ip int brief on sw1"
    ```

---

## 📚 Tools & Modules

* **`agent.nodes`**: Defines the graph state and interaction logic.
* **`utils.devices`**: Lazy-loads Nornir and injects secrets from environment variables.
* **`tools.show`**: Wraps `nornir_netmiko.netmiko_send_command`.
* **`tools.config`**: Wraps `nornir_netmiko.netmiko_send_config`.

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
