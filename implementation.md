Based on your logs, the "Error 400" happens because the `show running-config` output is too large and complex for the LLM to safely format back into a JSON tool call. The `AttributeError` you saw earlier confirms a mismatch between the new Prompt class and the Nodes using it.

Here is the fixed implementation to resolve both issues and handle large outputs gracefully.

### 1. Update `agent/prompts.py`

I've updated the **Format Prompt** to explicitly instruct the LLM **NOT** to dump large raw data (like configs) into the JSON, preventing the Error 400.

```python:agent/prompts.py
"""Collection of prompts for the Network Automation Agent."""

from langchain_core.prompts import ChatPromptTemplate


class NetworkAgentPrompts:
    """Collection of prompts for the Network Automation Agent."""

    # Context Manager Summary Prompt
    SUMMARY_PROMPT = ChatPromptTemplate.from_template(
        """Distill the following conversation history into a concise summary.
Include key details like device names, specific issues mentioned, and actions taken.
Do not lose important context needed for future turns.

Messages:
{messages_content}"""
    )

    # Understanding Node Prompt
    UNDERSTAND_PROMPT = ChatPromptTemplate.from_messages([
        ("system", """You are a network automation assistant.

Device inventory:
{device_inventory}

Role: Understand user requests and translate them into network operations or provide normal chat responses.

CRITICAL RULES - NEVER VIOLATE:
1. Device Names: ONLY use devices from the inventory above. NEVER make up or hallucinate device names.
2. No Fabrication: NEVER invent command outputs or network state. Wait for actual tool execution results.
3. Platform Awareness: Match command syntax to device platform (IOS, EOS, JunOS, etc.).
4. Tool Selection: Choose ONE tool per response based on user intent.

Available Tools:
{tools_description}

Decision Tree - When to use each tool:
- Simple single-device read operation → `show_command`
- Simple single-device configuration → `config_command`
- Complex multi-step or multi-device task → `multi_command`
- Informational query with no network action → `respond`

Multi-Device Operations:
- When targeting multiple devices, ensure commands are platform-specific
- Use device platform information from inventory to generate correct syntax

VALIDATION - Before calling any tool:
- Verify ALL device names exist in the inventory above
- Ensure commands are non-empty and syntactically valid
"""),
        ("placeholder", "{messages}")
    ])

    # Format Node Prompt
    FORMAT_PROMPT = ChatPromptTemplate.from_messages([
        ("system", """You are a network automation assistant analyzing command output.

Your task is to structure the following tool output into a clear, organized response.

Tool output to analyze:
{tool_output}

Call the format_output tool with:
- summary: A concise executive summary in Markdown format with device headings and bullet points
- structured_data: The parsed data as a dictionary or list
- errors: List of any errors (or null if none)

CRITICAL FORMATTING RULES:
1. Use device names as H2 headings (## Device Name) left-aligned
2. List key findings as bullet points under each device
3. Focus on operational status, health, and anomalies
4. LARGE DATA HANDLING: If the output is large raw text (like 'show running-config'), do NOT try to put the whole text into 'structured_data'. Instead, set 'structured_data' to an empty object {{}} or extract only specific key values. Reliance on the summary is preferred for large configs.

You MUST call the format_output tool. Do NOT return plain text.""")
    ])

    # Planner Node Prompt
    PLANNER_PROMPT = ChatPromptTemplate.from_template(
        """You are a network automation planner.
Your job is to break down complex user requests into a series of logical steps.

User Request: {user_request}

CRITICAL RULES:
- Reference ONLY devices from the user's network inventory (do NOT make up device names)
- Match commands to device platforms (IOS, EOS, JunOS, etc.)
- Each step must be specific, actionable, and executable
- Do NOT make assumptions about current network state
- Break down complex operations into simple, verifiable steps

Return a list of steps to accomplish this task.
Each step should be a clear, actionable description with specific device names and commands.
"""
    )
```

### 2. Update `agent/nodes/format_node.py`

Improved the fallback mechanism. If the LLM fails to format the data (Error 400), it will now cleanly display the raw output instead of crashing or showing a JSON error.

```python:agent/nodes/format_node.py
"""Format node for structuring tool outputs."""

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from agent.nodes.base_node import AgentNode
from agent.prompts import NetworkAgentPrompts
from core.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class FormatNode(AgentNode):
    """Format tool outputs using tool-based structured output."""

    def __init__(self, llm_provider: LLMProvider, format_tool):
        super().__init__(llm_provider)
        self._format_tool = format_tool

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Format tool output using format_output tool."""
        messages = state.get("messages", [])
        if not messages:
            return state

        # Get the last ToolMessage (the output to format)
        last_tool_msg = None
        for msg in reversed(messages):
            if isinstance(msg, ToolMessage):
                last_tool_msg = msg
                break

        if not last_tool_msg:
            return {"messages": [AIMessage(content="No tool output to format")]}

        # Use new ChatPromptTemplate
        prompt = NetworkAgentPrompts.FORMAT_PROMPT.invoke({
            "tool_output": last_tool_msg.content
        })

        try:
            # Bind format_output tool to LLM
            llm_with_tool = self._get_llm_with_tools([self._format_tool.to_langchain_tool()])

            # Invoke LLM with the formatted prompt
            response = llm_with_tool.invoke(prompt)

            # Check if LLM called the tool
            if hasattr(response, "tool_calls") and response.tool_calls:
                from langgraph.prebuilt import ToolNode
                tool_node = ToolNode([self._format_tool.to_langchain_tool()])
                tool_result = tool_node.invoke({"messages": [response]})
                return tool_result

            # Fallback: LLM didn't call the tool
            logger.warning("LLM did not call format_output tool, returning raw response")
            return {"messages": [response]}

        except Exception as e:
            logger.error(f"Format error: {e}")

            # Graceful Fallback: Return the raw content formatted nicely
            raw_content = last_tool_msg.content
            try:
                # If it's JSON, pretty print it
                parsed = json.loads(raw_content)
                pretty_json = json.dumps(parsed, indent=2)
                return {"messages": [AIMessage(content=f"```json\n{pretty_json}\n```")]}
            except Exception:
                # If text, just wrap it
                return {"messages": [AIMessage(content=f"```text\n{raw_content}\n```")]}
```

### 3. Update `agent/nodes/understanding_node.py`

Ensures strict compatibility with the new Prompts class to avoid `AttributeError`.

```python:agent/nodes/understanding_node.py
"""Understanding node for processing user input and selecting tools."""

import logging
from typing import Any

from agent.nodes.base_node import AgentNode
from agent.prompts import NetworkAgentPrompts
from core.device_inventory import DeviceInventory
from core.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class UnderstandingNode(AgentNode):
    """Understands user intent and selects tools."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        device_inventory: DeviceInventory,
        tools: list,
    ):
        super().__init__(llm_provider)
        self._device_inventory = device_inventory
        self._tools = tools

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Understand user intent and select tools."""
        messages = state.get("messages", [])

        # Get device inventory and tool descriptions
        inventory_str = self._device_inventory.get_device_info()
        tools_desc = self._format_tools_description(self._tools)

        # Generate prompt using ChatPromptTemplate
        prompt = NetworkAgentPrompts.UNDERSTAND_PROMPT.invoke({
            "device_inventory": inventory_str,
            "tools_description": tools_desc,
            "messages": messages
        })

        # Get LLM with tools and invoke
        llm_with_tools = self._get_llm_with_tools(self._tools)
        response = llm_with_tools.invoke(prompt)

        return {"messages": [response]}

    def _format_tools_description(self, tools: list) -> str:
        """Format tool descriptions for the prompt."""
        descriptions = []
        for tool in tools:
            name = getattr(tool, "name", str(tool))
            description = getattr(tool, "description", "")
            descriptions.append(f"- `{name}`: {description}")
        return "\n\n".join(descriptions)
```

### 4. Clean Up `agent/nodes/planner_node.py`

Standardizing the JSON parsing to match the rest of the app.

```python:agent/nodes/planner_node.py
"""Planner node for complex task breakdown."""

import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from utils.llm_helpers import parse_json_from_llm_response

from agent.nodes.base_node import AgentNode
from agent.prompts import NetworkAgentPrompts

logger = logging.getLogger(__name__)


class PlannerNode(AgentNode):
    """Generate step-by-step plans for complex requests."""

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Generate execution plan for the request."""
        messages = state.get("messages", [])
        if not messages:
            return state

        last_msg = messages[-1]
        user_request = last_msg.content if isinstance(last_msg, HumanMessage) else str(last_msg.content)

        # Generate plan using ChatPromptTemplate
        llm = self._get_llm()
        prompt = NetworkAgentPrompts.PLANNER_PROMPT.invoke({
            "user_request": user_request
        })

        # Add manual JSON instruction since we aren't using bind_tools here
        json_instruction = (
            "\n\nReturn your response as a JSON object with this exact format:\n"
            '{"steps": ["step 1 description", "step 2 description", ...]}'
        )

        # Combine prompt messages with instruction
        final_messages = prompt.to_messages()
        final_messages[-1].content += json_instruction

        try:
            response = llm.invoke(final_messages)

            # Use shared utility for robust JSON parsing
            parsed = parse_json_from_llm_response(response.content)

            if "steps" in parsed and isinstance(parsed["steps"], list):
                steps = parsed["steps"]
            else:
                raise ValueError("Invalid plan format - missing 'steps' array")

            plan_str = "I have created a plan:\n" + "\n".join(
                [f"{i + 1}. {step}" for i, step in enumerate(steps)]
            )
            return {"messages": [AIMessage(content=plan_str)]}

        except Exception as e:
            logger.error(f"Failed to generate plan: {e}")
            return {"messages": [AIMessage(content=f"Failed to generate plan: {str(e)}")]}
```

### 5. Update `agent/nodes/context_manager_node.py`

Ensuring it uses the new prompt class correctly.

```python:agent/nodes/context_manager_node.py
"""Context manager node for conversation history management."""

import logging
from typing import Any

from langchain_core.messages import SystemMessage, trim_messages
from langchain_core.messages.utils import count_tokens_approximately

from agent.nodes.base_node import AgentNode
from agent.prompts import NetworkAgentPrompts
from core.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class ContextManagerNode(AgentNode):
    """Manages conversation history and context window."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        max_history_tokens: int = 3500,
    ):
        super().__init__(llm_provider)
        self._max_history_tokens = max_history_tokens

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Manage conversation history and context window."""
        messages = state.get("messages", [])
        trimmed_msgs = self._trim_messages(messages)
        return {"messages": trimmed_msgs}

    def _trim_messages(self, messages: list) -> list:
        """Trim messages to fit within context window."""
        try:
            trimmed_msgs = trim_messages(
                messages,
                max_tokens=self._max_history_tokens,
                strategy="last",
                token_counter=count_tokens_approximately,
                start_on="human",
                include_system=False,
                allow_partial=False,
            )

            if len(messages) > len(trimmed_msgs):
                # Summarize dropped messages
                dropped_count = len(messages) - len(trimmed_msgs)
                if dropped_count > 0:
                    dropped_msgs = messages[:dropped_count]
                    summary = self._summarize_messages(dropped_msgs)
                    summary_msg = SystemMessage(content=f"Previous Conversation Summary:\n{summary}")
                    trimmed_msgs = [summary_msg] + trimmed_msgs
                    logger.info("Added conversation summary for dropped messages.")

            return trimmed_msgs

        except Exception as trim_error:
            logger.warning(f"Message trimming failed: {trim_error}. Using fallback.")
            return messages[-10:] if len(messages) > 10 else messages

    def _summarize_messages(self, messages: list) -> str:
        """Summarize messages using LLM."""
        llm = self._get_llm()

        # Prepare content string for the template
        content_parts = []
        for msg in messages:
            role = "User" if hasattr(msg, "role") and msg.role != "assistant" else "User"
            if hasattr(msg, "content"):
                content_parts.append(f"{role}: {msg.content}")

        # Use ChatPromptTemplate
        prompt = NetworkAgentPrompts.SUMMARY_PROMPT.invoke({
            "messages_content": "\n".join(content_parts)
        })

        response = llm.invoke(prompt)
        return response.content
```

### 6. Remove Dead Code

Please delete these files to clean up the workspace:

* `agent/nodes/router_node.py` (Deleted)
* `tests/unit/test_agent/test_router_node.py` (Deleted)
