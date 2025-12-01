"""Planner node for complex task breakdown.

This module provides the PlannerNode class that breaks down
complex network automation requests into step-by-step plans.
"""

import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field

from agent.nodes.base_node import AgentNode

logger = logging.getLogger(__name__)


PLANNER_PROMPT = """
You are a network automation planner.
Your job is to break down complex user requests into a series of logical steps.

User Request: {user_request}

Return a list of steps to accomplish this task.
Each step should be a clear, actionable description.
Do not generate code or commands yet, just the plan.
"""


class Plan(BaseModel):
    """A list of steps to complete a task."""

    steps: list[str] = Field(description="List of steps to execute.")


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

        # Generate plan using structured LLM
        structured_llm = self._get_structured_llm(Plan)
        prompt = PLANNER_PROMPT.format(user_request=user_request)

        try:
            plan = structured_llm.invoke(prompt)

            # Format plan as a numbered list
            plan_str = "I have created a plan:\n" + "\n".join(
                [f"{i + 1}. {step}" for i, step in enumerate(plan.steps)]
            )

            logger.info(f"Generated plan with {len(plan.steps)} steps")

            return {"messages": [AIMessage(content=plan_str)]}

        except Exception as e:
            logger.error(f"Failed to generate plan: {e}")
            return {"messages": [AIMessage(content=f"Failed to generate plan: {str(e)}")]}
