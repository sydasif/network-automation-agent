# Configuration Guide

This document provides detailed information about configuring the Network Automation Agent.

## Table of Contents
- [Environment Setup](#environment-setup)
- [Application Configuration](#application-configuration)
- [Device Inventory](#device-inventory)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)

## Environment Setup

### Prerequisites

- Python 3.12+
- `uv` package manager (recommended)
- Groq API key
- Network devices with SSH access

### Installation

1. Install `uv` package manager:
   ```bash
   pip install uv
   ```

2. Clone and install dependencies:
   ```bash
   git clone <repository-url>
   cd network-automation-agent
   uv sync
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env and add your GROQ_API_KEY
   ```

## Application Configuration

The main configuration is handled through `config.yaml`, which uses Nornir's configuration format.

### config.yaml Structure

```yaml
---
# Nornir Configuration for Network Automation Agent
inventory:
  plugin: SimpleInventory
  options:
    host_file: "hosts.yaml"
    group_file: "groups.yaml"
runner:
  plugin: threaded
  options:
    # Number of parallel workers (can be overridden with NUM_WORKERS env var)
    num_workers: 20
logging:
  enabled: false
defaults:
  connection_options:
    netmiko:
      extras:
        # Timeouts can be overridden via environment variables
        timeout: 30
        conn_timeout: 10
        session_timeout: 60
```

### Environment Variables

#### Required Variables
- `GROQ_API_KEY`: Your Groq API key for AI processing

#### Optional Variables
- `NUM_WORKERS`: Number of concurrent connections to devices (default: 20)
- `NETMIKO_TIMEOUT`: Command execution timeout in seconds (default: 30)
- `NETMIKO_CONN_TIMEOUT`: Connection timeout in seconds (default: 10)
- `NETMIKO_SESSION_TIMEOUT`: Session timeout in seconds (default: 60)

## Device Inventory

The agent uses two files to define network devices: `hosts.yaml` and `groups.yaml`.

### hosts.yaml

This file defines individual network devices:

```yaml
---
# Example hosts.yaml
r1:
  hostname: 192.168.1.101
  groups: [cisco]
  port: 22
  username: admin  # Optional: overrides group default
  password: secret  # Optional: overrides group default

s1:
  hostname: 192.168.1.102
  groups: [arista]
  port: 22

router2:
  hostname: 10.0.0.1
  groups: [cisco, production]
  data:
    site: "Data Center 1"
    role: "Core Router"
```

### groups.yaml

This file defines device groups and their common settings:

```yaml
---
# Example groups.yaml
cisco:
  platform: cisco_ios
  username: admin
  password: admin
  connection_options:
    netmiko:
      extras:
        device_type: cisco_ios
        timeout: 30

arista:
  platform: arista_eos
  username: admin
  password: admin
  connection_options:
    netmiko:
      extras:
        device_type: arista_eos
        timeout: 30

juniper:
  platform: juniper_junos
  username: admin
  password: admin123
  connection_options:
    netmiko:
      extras:
        device_type: juniper_junos
        timeout: 30

production:
  data:
    environment: production
    maintenance_window: "Sat 2-6 AM"
```

### Platform Support

The agent supports various network platforms through Netmiko:

- `cisco_ios` - Cisco IOS
- `cisco_xe` - Cisco IOS XE
- `cisco_xr` - Cisco IOS XR
- `arista_eos` - Arista EOS
- `juniper_junos` - Juniper Junos
- `hp_procurve` - HP ProCurve
- `nokia_sros` - Nokia SR OS

For a complete list of supported platforms, refer to the Netmiko documentation.

## Security Considerations

### Credential Management

- Never commit credential files to version control
- Use environment variables or secure credential stores in production
- Consider using SSH keys instead of passwords when possible
- Regularly rotate credentials

### Network Security

- Ensure network devices are accessible only through secure channels
- Use VPN or dedicated management networks when possible
- Implement proper firewall rules to limit access
- Monitor network traffic for unusual patterns

### API Key Security

- Store your GROQ_API_KEY securely
- Rotate your API key periodically
- Monitor API usage for unusual patterns
- Use environment variables or secure vaults to store keys

## Validation and Safety Features

### Device Validation

The agent validates that target devices exist in the inventory before execution. This prevents accidental commands to non-existent devices.

### Command Validation

All commands are validated before execution to ensure they are safe and appropriate for the target device type.

### Risk Assessment

Configuration commands are assessed for potential risks before requiring human approval.

## Troubleshooting

### Common Issues

#### Connection Problems
- Verify SSH connectivity to devices: `ssh username@hostname`
- Check that the device platform is correctly specified
- Verify credentials are correct
- Check that the device is reachable on the network

#### API Key Issues
- Ensure GROQ_API_KEY is set in the environment
- Verify the API key is valid and not expired
- Check that the API service is accessible

#### Configuration Errors
- Verify YAML syntax is correct
- Ensure all required fields are present
- Check that file paths are correct

### Debugging

Enable debug mode to get more detailed information:

```bash
uv run python main.py --chat --debug
```

### Logging

The application provides different levels of logging:
- `WARNING` in chat mode (clean UI)
- `INFO` in single command mode (execution progress)
- `DEBUG` when using `--debug` flag (detailed information)

Log files are stored in the application directory and follow the naming pattern `network_agent.log`.