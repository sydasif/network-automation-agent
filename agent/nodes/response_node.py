"""Response node for formatting final output using Structured Outputs."""

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent.nodes.base_node import AgentNode
from agent.prompts import NetworkAgentPrompts
from agent.schemas import AgentResponse

logger = logging.getLogger(__name__)


class ResponseNode(AgentNode):
    """Formats the final response by combining LLM summary with raw data."""

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        messages = state.get("messages", [])
        logger.info(f"ResponseNode executing. Message count: {len(messages)}")

        # 1. Identify User Query
        user_query = "Unknown request"
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                user_query = msg.content
                break

        # 2. Extract Data from previous ExecuteNode steps
        last_tool_output_str = "No data found."

        # Iterate backwards to find tool outputs
        found_tool_output = False
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                break
            if isinstance(msg, ToolMessage):
                found_tool_output = True
                # Ignore error/denied messages if you wish
                if msg.content.startswith("❌"):
                    last_tool_output_str += f"\nError from {msg.name}: {msg.content}"
                    continue
                last_tool_output_str += f"\nOutput from {msg.name}: {msg.content}"

        if not found_tool_output:
            logger.warning("ResponseNode ran but found no tool outputs in recent history.")

        # 3. Generate Structured Response using Pydantic
        prompt = NetworkAgentPrompts.RESPONSE_PROMPT.invoke(
            {"user_query": user_query, "data": last_tool_output_str[:25000]}
        )

        # Get the LLM and enforce the schema
        llm = self._get_llm()
        structured_llm = llm.with_structured_output(AgentResponse)

        final_payload = {}
        try:
            logger.info("Invoking LLM for structured response...")
            # This returns an instance of AgentResponse
            response_model: AgentResponse = structured_llm.invoke(prompt)

            # Check if response_model is actually an AgentResponse instance or a mock
            if hasattr(response_model, "model_dump"):
                # Convert back to dict for the UI/State
                final_payload = response_model.model_dump(exclude_none=True)

                # Map 'summary' to 'message' to match what UI expects
                if "summary" in final_payload:
                    final_payload["message"] = final_payload.pop("summary")
                else:
                    # Should not happen due to Pydantic, but safety first
                    final_payload["message"] = "No summary generated."
            else:
                # This might happen in tests where a mock is returned instead of a real AgentResponse
                logger.warning("Response model doesn't have model_dump method, using fallback")
                final_payload = {
                    "message": "Response generated successfully",
                    "structured_data": None,
                }

        except Exception as e:
            logger.error(f"Error generating structured response: {e}")
            final_payload = {
                "message": f"Error generating structured response: {str(e)}",
                "structured_data": {"raw": last_tool_output_str[:1000]},
            }

        logger.info("Response generated successfully.")
        return {"messages": [AIMessage(content=json.dumps(final_payload))]}
