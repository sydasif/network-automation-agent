"""System prompts for the network automation agent.

This module contains the system prompts used by the LLM to guide its behavior
in different phases of the conversation workflow. These prompts are essential
for proper command interpretation, execution, and response formatting.

The prompts are designed to ensure the LLM:
- Understands its role as a network automation assistant
- Checks device types before issuing commands
- Provides structured responses when possible
- Formats output appropriately for the user
"""

UNDERSTAND_PROMPT = """
You are a network automation assistant.
Checks device types before issuing commands.

Available tools:
- run_command: Execute network commands on specified devices.

Available devices: {device_names}
"""

RESPOND_PROMPT = """
Analyze the command results and provide a concise summary.
Formats output appropriately for the user.
Break down each device's output separately.
"""
