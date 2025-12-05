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
        user_request = (
            last_msg.content if isinstance(last_msg, HumanMessage) else str(last_msg.content)
        )

        # Generate plan using ChatPromptTemplate
        llm = self._get_llm()
        prompt = NetworkAgentPrompts.PLANNER_PROMPT.invoke({"user_request": user_request})

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
