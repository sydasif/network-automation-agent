"""Planner node for complex task breakdown.

This module provides the PlannerNode class that breaks down
complex network automation requests into step-by-step plans.
"""

import json
import logging
import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from agent.nodes.base_node import AgentNode
from agent.prompts import NetworkAgentPrompts

logger = logging.getLogger(__name__)


class PlannerNode(AgentNode):
    """Generate step-by-step plans for complex requests.

    This node analyzes complex network automation requests and
    breaks them down into logical, sequential steps.
    """

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Generate execution plan for the request.

        Args:
            state: Current workflow state

        Returns:
            Updated state with plan as AI message
        """
        messages = state.get("messages", [])
        if not messages:
            return state

        last_msg = messages[-1]

        # Extract user request content
        if isinstance(last_msg, HumanMessage):
            user_request = last_msg.content
        else:
            # Fallback: use the last message content
            user_request = str(last_msg.content)

        # Generate plan using plain LLM (not structured output for Groq compatibility)
        llm = self._get_llm()
        prompt = NetworkAgentPrompts.planner_system(user_request)

        # Add JSON format instruction
        json_instruction = (
            "\n\nReturn your response as a JSON object with this exact format:\n"
            '{"steps": ["step 1 description", "step 2 description", ...]}'
        )
        full_prompt = prompt + json_instruction

        try:
            response = llm.invoke(full_prompt)
            response_text = response.content

            # Try to extract JSON from the response
            try:
                # First try: parse whole response as JSON
                parsed = json.loads(response_text)
            except json.JSONDecodeError:
                # Second try: find JSON in markdown code blocks
                json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(1))
                else:
                    # Third try: find JSON object in text
                    json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group(0))
                    else:
                        raise ValueError("No JSON found in response")

            # Validate and extract steps
            if "steps" in parsed and isinstance(parsed["steps"], list):
                steps = parsed["steps"]
            else:
                raise ValueError("Invalid plan format - missing 'steps' array")

            # Format plan as a numbered list
            plan_str = "I have created a plan:\n" + "\n".join(
                [f"{i + 1}. {step}" for i, step in enumerate(steps)]
            )

            logger.info(f"Generated plan with {len(steps)} steps")

            return {"messages": [AIMessage(content=plan_str)]}

        except Exception as e:
            logger.error(f"Failed to generate plan: {e}")
            return {"messages": [AIMessage(content=f"Failed to generate plan: {str(e)}")]}
