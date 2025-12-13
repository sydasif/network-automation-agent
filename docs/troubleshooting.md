# Troubleshooting Guide

This document provides troubleshooting information for common issues with the Network Automation Agent.

## Table of Contents
- [Installation Issues](#installation-issues)
- [Configuration Problems](#configuration-problems)
- [Connection Issues](#connection-issues)
- [LLM/Service Issues](#llm-service-issues)
- [Validation Errors](#validation-errors)
- [Workflow Issues](#workflow-issues)
- [Performance Issues](#performance-issues)
- [Security Considerations](#security-considerations)

## Installation Issues

### Dependency Installation Problems

**Problem**: `uv sync` fails with dependency conflicts.

**Solution**:
1. Update uv to the latest version:
   ```bash
   pip install -U uv
   ```
2. Clear the cache and try again:
   ```bash
   uv cache clean
   uv sync
   ```

**Problem**: Python version compatibility issues.

**Solution**: Ensure you're using Python 3.12+:
```bash
python --version
# If not using Python 3.12+, use pyenv or your system's package manager to install Python 3.12+
```

### Missing Dependencies

**Problem**: Import errors after installation.

**Solution**:
1. Verify all dependencies are installed:
   ```bash
   uv sync
   ```
2. If using a virtual environment, ensure it's activated:
   ```bash
   source .venv/bin/activate  # If using uv's virtual environment
   ```

## Configuration Problems

### Environment Variables

**Problem**: "GROQ_API_KEY not found" error.

**Solution**:
1. Ensure `.env` file exists in the project root
2. Verify the API key is properly set:
   ```bash
   echo $GROQ_API_KEY
   ```
3. If not set, add it to your `.env` file:
   ```
   GROQ_API_KEY=your_actual_api_key_here
   ```

### Inventory Configuration

**Problem**: "Device not found" errors.

**Solution**:
1. Verify device names in `hosts.yaml` match what you're using in commands
2. Check that `groups.yaml` has correct platform and credential information
3. Ensure device hostnames are valid (alphanumeric, dots, underscores, hyphens only)

Example correct format:
```yaml
# hosts.yaml
r1:
  hostname: 192.168.1.101
  groups: [cisco]

# groups.yaml
cisco:
  platform: cisco_ios
  username: admin
  password: secure_password
```

### Invalid YAML Format

**Problem**: YAML parsing errors.

**Solution**:
1. Validate YAML syntax using online validators or:
   ```bash
   python -c "import yaml; print(yaml.safe_load(open('config.yaml')))"
   ```
2. Ensure consistent indentation (use spaces, not tabs)
3. Check for missing colons, quotes, or brackets

## Connection Issues

### Device Connectivity

**Problem**: "Connection timed out" errors.

**Solution**:
1. Verify network connectivity to devices:
   ```bash
   ping device_ip_address
   ssh username@device_ip_address
   ```
2. Check firewall rules blocking SSH (port 22 by default)
3. Verify device is reachable and SSH service is running
4. Adjust timeout values in `config.yaml`:
   ```yaml
   defaults:
     connection_options:
       netmiko:
         extras:
           timeout: 60  # Increase if devices are slow to respond
           conn_timeout: 20
   ```

### Authentication Failures

**Problem**: "Authentication failed" errors.

**Solution**:
1. Verify credentials in `groups.yaml` are correct
2. Check that username and password match device configuration
3. Ensure device accepts SSH key-based authentication if configured
4. Test manual SSH connection to verify credentials work

### Platform Compatibility

**Problem**: "Invalid device_type" or platform-specific errors.

**Solution**:
1. Verify platform is correctly specified in `groups.yaml`
2. Check that platform name matches Netmiko's supported platforms
3. Common platform names:
   - `cisco_ios` for Cisco IOS
   - `cisco_xe` for Cisco IOS XE
   - `cisco_xr` for Cisco IOS XR
   - `arista_eos` for Arista EOS
   - `juniper_junos` for Juniper Junos

## LLM/Service Issues

### API Key Problems

**Problem**: "Invalid API key" or "Unauthorized" errors.

**Solution**:
1. Verify API key is correctly set in environment
2. Check for typos in the API key
3. Ensure API key has sufficient quota/usage allowance
4. Test API key validity by making a direct call to the service

### Rate Limiting

**Problem**: "Rate limit exceeded" errors.

**Solution**:
1. Check your Groq API usage limits
2. Implement appropriate delays between requests if needed
3. Consider upgrading your API plan if hitting limits frequently

### LLM Response Issues

**Problem**: "Planning failed" or structured output errors.

**Solution**:
1. Check that the LLM is returning properly structured responses
2. Verify that the Pydantic schema matches what the LLM is expected to return
3. Look for "Invalid response model" warnings in logs

## Validation Errors

### Device Validation

**Problem**: "No devices specified" or "Invalid device name" errors.

**Solution**:
1. Ensure device names are provided in commands
2. Verify device names match exactly what's in your inventory
3. Check that device names follow allowed format (alphanumeric, dots, underscores, hyphens)

### Command Validation

**Problem**: "Invalid command format" or "Command appears to be a configuration command" errors.

**Solution**:
1. For show commands, ensure they start with "show", "display", or "sh"
2. For configuration commands, use the `config_command` tool instead of `show_command`
3. Verify command syntax is appropriate for the target device platform

### Dangerous Command Prevention

**Problem**: "appears to be a destructive operation" errors.

**Solution**:
1. These are safety features preventing dangerous commands via show_command
2. Use the config_command tool for actual configuration changes
3. Commands like "delete", "format", "erase", "reload", "reboot" should be intentional configuration changes

## Workflow Issues

### Tool Execution Problems

**Problem**: Tools not executing or returning unexpected results.

**Solution**:
1. Check logs for detailed error messages
2. Verify that the task executor is properly initialized
3. Ensure devices are available and reachable during execution
4. Check that the tool registry has the required tools registered

### Approval Process Issues

**Problem**: Configuration changes not requiring approval or approval not working.

**Solution**:
1. Verify that config commands trigger the approval node
2. Check that the approval workflow is properly configured
3. Ensure the interrupt mechanism is working correctly

### State Management Problems

**Problem**: Workflow state not persisting or unexpected state transitions.

**Solution**:
1. Check that the MemorySaver is properly initialized
2. Verify state transitions are following the expected linear flow
3. Look for any circular dependencies in the workflow

## Performance Issues

### Slow Response Times

**Problem**: Long delays in command execution or response generation.

**Solution**:
1. Check network latency to devices
2. Verify device performance (high CPU usage can slow responses)
3. Adjust `num_workers` in `config.yaml` if processing many devices
4. Consider increasing timeout values if devices are slow

### Memory Usage

**Problem**: High memory consumption during long sessions.

**Solution**:
1. The message manager should automatically compress old messages
2. Check that `max_history_tokens` is set appropriately in config
3. Monitor memory usage during extended use

### Connection Pooling

**Problem**: Connection issues when targeting many devices simultaneously.

**Solution**:
1. Adjust `num_workers` in `config.yaml` to limit concurrent connections
2. The system includes a 1-second delay between operations to prevent "Prompt not detected" errors
3. Consider staggering large operations across multiple requests

## Security Considerations

### Credential Management

**Problem**: Credentials stored in plain text.

**Solution**:
1. Never commit credential files to version control
2. Use environment variables or secure credential stores in production
3. Regularly rotate device credentials
4. Consider using SSH keys instead of passwords when possible

### API Key Security

**Problem**: API key exposure risks.

**Solution**:
1. Store API keys securely and never commit to version control
2. Use environment variables or secure vaults
3. Monitor API usage for unusual patterns
4. Rotate API keys regularly

### Network Security

**Problem**: Unencrypted communication with network devices.

**Solution**:
1. Ensure SSH is used for all device connections
2. Use VPN or dedicated management networks when possible
3. Implement proper firewall rules to limit access
4. Monitor network traffic for unusual patterns

## Debugging Tips

### Enable Debug Mode

To get more detailed information about what's happening:

```bash
uv run python main.py --chat --debug
```

### Check Logs

Logs are written to `network_agent.log` in the project directory. Look for:
- Error messages with stack traces
- Connection and authentication issues
- Validation failures
- Workflow state changes

### Test Individual Components

You can test individual components separately:

```bash
# Test configuration loading
python -c "from core.config import NetworkAgentConfig; print(NetworkAgentConfig.load())"

# Test device inventory
python -c "from core.device_inventory import DeviceInventory; print(DeviceInventory.load().get_all_device_names())"
```

### Common Error Patterns

- **JSON serialization errors**: Usually related to mock objects in tests or invalid response formats
- **Connection timeouts**: Often network-related or due to device overload
- **Validation errors**: Usually indicate invalid device names or command formats
- **API errors**: Typically related to missing or invalid API keys

## Getting Help

If you encounter issues not covered in this guide:

1. Check the logs for detailed error information
2. Verify all configuration files are properly formatted
3. Ensure network connectivity to target devices
4. Confirm API keys and credentials are correct
5. Run the test suite to verify basic functionality:
   ```bash
   uv run pytest
   ```