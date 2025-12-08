"""Response node for formatting final output using Structured Outputs."""

import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from agent.nodes.base_node import AgentNode
from agent.prompts import NetworkAgentPrompts
from agent.schemas import AgentResponse


class ResponseNode(AgentNode):
    """Formats the final response by combining LLM summary with raw data."""

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        messages = state.get("messages", [])

        # 1. Identify User Query
        user_query = "Unknown request"
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                user_query = msg.content
                break

        # 2. Extract Data from previous ExecuteNode steps
        last_tool_output_str = "No data found."

        # Iterate backwards to find tool outputs
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                break
            if isinstance(msg, ToolMessage):
                # Ignore error/denied messages if you wish
                if msg.content.startswith("❌"):
                    last_tool_output_str += f"\nError from {msg.name}: {msg.content}"
                    continue
                last_tool_output_str += f"\nOutput from {msg.name}: {msg.content}"

        # 3. Generate Structured Response using Pydantic
        prompt = NetworkAgentPrompts.RESPONSE_PROMPT.invoke({
            "user_query": user_query,
            "data": last_tool_output_str[:25000]
        })

        # Get the LLM and enforce the schema
        llm = self._get_llm()
        structured_llm = llm.with_structured_output(AgentResponse)

        try:
            # This returns an instance of AgentResponse
            response_model: AgentResponse = structured_llm.invoke(prompt)

            # Convert back to dict for the UI/State
            final_payload = response_model.model_dump(exclude_none=True)

            # Map 'summary' to 'message' to match what UI expects
            final_payload["message"] = final_payload.pop("summary")

            return {
                "messages": [AIMessage(content=json.dumps(final_payload))]
            }

        except Exception as e:
            # Fallback if strict parsing fails
            return {
                "messages": [AIMessage(content=json.dumps({
                    "message": f"Error generating structured response: {str(e)}",
                    "structured_data": {"raw": last_tool_output_str[:1000]}
                }))]
            }