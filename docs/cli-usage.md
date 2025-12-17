# CLI Usage Guide

This document provides detailed information about using the Network Automation Agent command-line interface.

## Table of Contents
- [Overview](#overview)
- [Command-Line Options](#command-line-options)
- [Usage Modes](#usage-modes)
- [Examples](#examples)
- [Advanced Usage](#advanced-usage)

## Overview

The Network Automation Agent provides a command-line interface that allows you to interact with network devices using natural language commands. The CLI supports both interactive chat mode and single command execution.

## Command-Line Options

### Main Options

- `--chat, -c`: Start interactive chat mode (default when no command provided)
- `--device DEVICE, -d DEVICE`: Target device for the command (recommended)
- `--debug`: Enable debug logging
- `--monitor, -m`: Show monitoring dashboard and exit
- `--help`: Show help message and exit

### Usage Syntax

```bash
uv run python main.py [options] [command...]
```

## Usage Modes

### Interactive Chat Mode

Interactive chat mode provides a conversational interface for network automation tasks.

**Command:**
```bash
uv run python main.py --chat
```

**Alternative (default when no command provided):**
```bash
uv run python main.py --chat
# or
uv run python main.py
```

**Features:**
- Natural language conversation with the agent
- Context-aware responses
- Support for multi-step workflows
- Command history
- Real-time feedback

### Single Command Mode

Single command mode executes one command and exits.

**Command:**
```bash
uv run python main.py "your command here"
```

**Example:**
```bash
uv run python main.py "show ip interface brief on R1"
```

## Examples

### Basic Commands

**Show command on specific device:**
```bash
uv run python main.py "show version on R1"
```

**Show command with device flag:**
```bash
uv run python main.py --device R1 "show ip interface brief"
```

**Configuration command:**
```bash
uv run python main.py "configure interface loopback0 on R1 with ip address 10.0.0.1 255.255.255.255"
```

### Interactive Mode Examples

**Starting interactive mode:**
```bash
uv run python main.py --chat
```

**In interactive mode, you can ask:**
```
> Show me the interface status on R1
> What's the OSPF configuration on router2?
> Configure VLAN 10 on switch1
> Compare the running config with startup config on R1
```

### Advanced Examples

**Target specific device:**
```bash
uv run python main.py --device s1 "show vlan brief"
```

**Debug mode with detailed output:**
```bash
uv run python main.py --debug "show running-config on R1"
```

**Multiple commands in interactive mode:**
```
> Show me the interface status on all devices
> Can you configure NTP server 10.0.0.1 on all Cisco devices?
> What's the BGP status?
```

## Command Patterns

The agent understands various command patterns:

### Show Commands
- "Show [command] on [device]"
- "Display [command] from [device]"
- "[command] on [device]"
- "What is [information] on [device]?"

### Configuration Commands
- "Configure [feature] on [device]"
- "Set [parameter] on [device]"
- "Change [setting] on [device]"
- "Add [configuration] to [device]"

### Device References
- Device names as defined in `hosts.yaml` (e.g., R1, s1, router2)
- Device groups as defined in `groups.yaml` (e.g., all cisco devices)
- IP addresses (if directly accessible)

## Safety Features

### Human Approval
Configuration commands require explicit approval before execution:
```
> Configure interface loopback100 on R1 with ip address 192.168.100.1 255.255.255.255

The agent will display the command to be executed and ask for confirmation:
"Would you like to execute this configuration? (y/N): "
```

### Validation
- Device existence validation
- Command syntax validation
- Risk assessment for configuration changes
- Multi-vendor command compatibility checking

## Troubleshooting CLI Issues

### Common Problems

**Command not recognized:**
- Ensure your command uses natural language
- Verify device name exists in inventory
- Check for typos in device names

**Connection errors:**
- Verify network connectivity to the device
- Check credentials in groups.yaml
- Confirm device platform is correctly specified

**API errors:**
- Verify GROQ_API_KEY is set correctly
- Check internet connectivity
- Verify API key has sufficient quota

### Debugging Commands

**Enable debug mode:**
```bash
uv run python main.py --debug "your command"
```

**Check configuration:**
```bash
# Verify environment variables
env | grep GROQ

# Verify inventory files exist
ls -la hosts.yaml groups.yaml config.yaml
```

## Monitoring Dashboard

The Network Automation Agent includes a comprehensive monitoring dashboard that provides real-time insights into system performance, workflow execution, and system health.

### Accessing the Dashboard

To view the monitoring dashboard:

```bash
uv run python main.py --monitor
# or
uv run python main.py -m
```

The dashboard displays:

- **System Status**: Overall health status and performance score
- **Performance Metrics**: Average tool execution time, LLM response time, and success rates
- **Recent Sessions**: List of recent workflow sessions with execution details
- **Alert Summary**: Count of recent alerts by type and severity
- **Recent Alerts**: Details of the most recent alerts

### Dashboard Features

- **Performance Indicators**: Color-coded status indicators (✅ Good, ⚠️ Warning, ❌ Critical)
- **Session Tracking**: Monitor individual workflow sessions with detailed metrics
- **Alert Management**: View and track system alerts with severity levels

## Advanced Usage

### Environment Variables

You can override configuration with environment variables:

```bash
# Override number of workers
NUM_WORKERS=10 uv run python main.py --chat

# Override timeout values
NETMIKO_TIMEOUT=60 uv run python main.py "show running-config on R1"
```

### Working with Device Groups

You can target device groups defined in your inventory:

```
> Show version on all cisco devices
> Configure NTP on devices in production group
```

### Combining Options

```bash
# Interactive mode with debug output
uv run python main.py --chat --debug

# Single command with specific device
uv run python main.py --device R1 --debug "show ip route"
```

## Best Practices

1. **Always specify devices clearly** to avoid targeting wrong equipment
2. **Use interactive mode** for complex multi-step operations
3. **Review configuration changes** before approving them
4. **Test commands** in non-production environments first
5. **Use debug mode** when troubleshooting connection issues
6. **Keep credentials secure** and never commit them to version control

## Exit Codes

- `0`: Success
- `1`: General error
- `2`: Command-line argument error
- `10`: Configuration error
- `20`: Connection error
- `30`: API error