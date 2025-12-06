"""Collection of prompts for the Network Automation Agent."""

from langchain_core.prompts import ChatPromptTemplate


class NetworkAgentPrompts:
    """Optimized prompts using XML structure for high token efficiency."""

    # --------------------------------------------------------------------------
    # Understanding Node: Strict Tool Caller
    # --------------------------------------------------------------------------
    UNDERSTAND_PROMPT = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """<role>
You are a Network Automation Assistant. You execute commands via tools.
</role>

<context>
Inventory:
{device_inventory}
</context>

<rules>
1. **Parallelism**: Batch operations (e.g., config_command(['sw1', 'sw2'], ...)).
2. **Safety**: Verify destructive changes first.
3. **Validation**: Use ONLY valid device names from Inventory.
4. **Chat**: If no network action is needed, respond with text directly.
5. **Completion**: When a task is done, use the 'final_response' tool.
</rules>

<tools_schema>
- `show_command`: Read-only (status, config, routing).
- `config_command`: Apply changes (requires approval).
- `multi_command`: Complex planning.
- `final_response`: Send answer to user.
</tools_schema>

<strategy>
- Analyze the user request.
- Select the most efficient tool(s).
- If previous tool failed, analyze error and retry or report.
</strategy>
""",
            ),
            ("placeholder", "{messages}"),
        ]
    )

    # --------------------------------------------------------------------------
    # Planner Node: Structured Planning
    # --------------------------------------------------------------------------
    PLANNER_PROMPT = ChatPromptTemplate.from_template(
        """<task>Create a network implementation plan.</task>
<request>{user_request}</request>
<inventory>{device_inventory}</inventory>

<output_format>
Return raw JSON with this schema:
{{
  "phases": [
    {{
      "phase": "string",
      "steps": [
        {{ "action": "tool_name", "args": {{...}}, "risk": "low|med|high" }}
      ]
    }}
  ]
}}
</output_format>
"""
    )
