# Network AI Agent

## Why Network AI Agent?

In today's complex network environments, managing and troubleshooting devices can be a time-consuming and error-prone task. The Network AI Agent was created to address these challenges by providing a powerful, yet intuitive, solution for network automation. By leveraging the power of AI, this tool simplifies network management, reduces manual effort, and empowers network engineers to focus on more strategic initiatives.

## Features

- **AI-Powered Network Commands**: Use natural language to manage network devices.
- **Multi-Device Support**: Execute commands across multiple devices simultaneously.
- **Parallel Execution**: Efficiently process commands in parallel using `ThreadPoolExecutor`.
- **Structured Output**: Receive beautifully formatted output, especially for interface data, thanks to `tabulate`.
- **Workflow Management**: Manage complex network workflows with a state machine powered by `LangGraph`.
- **Secure Device Access**: Ensure secure device communication with SSH connectivity via `netmiko`.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- `uv` package manager
- SSH access to your network devices
- A Groq API key for AI functionality

### Installation and Configuration

1. **Clone the repository and navigate to the project directory**:

    ```bash
    git clone https://github.com/sydasif/network-automation-agent.git
    cd network-agent
    ```

2. **Install the required dependencies**:

    ```bash
    uv sync
    ```

3. **Configure your environment**:

    ```bash
    cp .env.example .env
    ```

    Then, add your Groq API key to the newly created `.env` file.

4. **Configure and Migrate Your Network Devices**:

   The device inventory is now managed by a SQLite database (`inventory.db`) for improved performance and scalability. To populate it, follow this two-step process:

   **Step 1: Configure `hosts.yaml`**

   First, add your network device details to the `hosts.yaml` file. This file is used only for the initial data migration.

    ```yaml
    devices:
      - name: router-1
        host: 192.168.1.10
        username: admin
        password: password123
        device_type: cisco_ios
      - name: switch-1
        host: 192.168.1.11
        username: admin
        password: password123
        device_type: cisco_ios
    ```

   **Step 2: Run the Migration Script**

   Next, run the migration script to create the database and import the devices from your `hosts.yaml` file:

    ```bash
    uv run hosts.py
    ```

   This will create an `inventory.db` file. Once the migration is complete, the `hosts.yaml` file is no longer used for operations.

## Usage

To run the agent in interactive mode, use the following command:

```bash
uv run main.py
```

You can then enter commands in natural language, such as:

- "Show me the version of router-1"
- "Show interfaces on switch-1"
- "Show version on all devices"
- "Show running-config on router-1 and switch-1"

To exit the agent, simply type `quit`.

## Example Usage

Here's an example conversation showing how to interact with the Network AI Agent:

```markdown
🤖 Network AI Agent Ready!
Type 'quit' to exit.

You: Hi, who are you and what you can do?

🤖 Agent: Hello! I’m your network automation assistant, here to help you manage and troubleshoot your network devices.
I can:

- **Run show commands** on the devices in your environment (currently `s1` and `s2`).
- **Parse the output** into structured data so you can easily extract information like interface status, routing tables, or configuration details.
- **Return the results in JSON** so you can feed them into scripts, dashboards, or other automation tools.

Just let me know which command you'd like to run and on which device(s), and I'll take care of the rest!

You: ok, can you check only those vlan which are used on device s1.

🤖 Agent: **VLANs currently in use on device `s1`**

| VLAN ID | VLAN Name   | Status | Interfaces in use |
|---------|-------------|--------|-------------------|
| 1       | default     | active | Et0/2, Et0/3      |

All other VLANs (10, 20, 1002-1005) are defined but have no interfaces assigned, so they're not actively used on `s1`.

You: and device s1 version with uptime only.

🤖 Agent: **Device `s1` – Version & Uptime**

| Item          | Value                     |
|---------------|---------------------------|
| Software Image| X86_64BI_LINUX_L2-ADVENTERPRISEK9-M |
| Version       | 17.15.1                   |
| Uptime        | 30 minutes                |

You: Good, thanks.

🤖 Agent: You're welcome! If you need anything else, just let me know.

You: quit
Goodbye!
```

## Architecture

The agent is built on a `LangGraph`-based state machine with three main nodes:

1. **Understand**: Parses the user's intent to extract device names and commands.
2. **Execute**: Runs the network commands on the specified devices.
3. **Respond**: Formats and returns the results to the user.

```text
+-----------------+      +-----------------+      +-----------------+
|                 |      |                 |      |                 |
|   Understand    +---->     Execute     +---->     Respond     |
| (Parse Intent)  |      | (Run Commands)  |      | (Format Output) |
|                 |      |                 |      |                 |
+-----------------+      +-----------------+      +-----------------+
```

## Supported Commands

The agent can execute any command supported by your network devices, with special formatting for:

- `show version`
- `show interfaces`
- `show ip route`
- `show running-config`
- `show startup-config`

## Contributing

Contributions are welcome! If you'd like to contribute to this project, please follow these steps:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature/your-feature-name`).
3. Make your changes and commit them (`git commit -m 'Add some feature'`).
4. Push to the branch (`git push origin feature/your-feature-name`).
5. Open a pull request.

Please make sure to update tests as appropriate.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
