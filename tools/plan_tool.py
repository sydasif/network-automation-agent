"""Planning tool for complex network automation tasks.

This module provides the PlannerTool class for breaking down
complex requests into step-by-step execution plans.
"""

from pydantic import BaseModel, Field

from tools.base_tool import NetworkTool


class PlanInput(BaseModel):
    """Input schema for planning tasks."""

    request: str = Field(description="The user's request to plan for.")


class PlannerTool(NetworkTool):
    """Generate step-by-step execution plans for complex requests.

    This tool analyzes complex network automation requests and breaks
    them down into logical, sequential steps.
    """

    @property
    def name(self) -> str:
        """Tool name."""
        return "plan_task"

    @property
    def description(self) -> str:
        """Tool description."""
        return (
            "Generate a step-by-step execution plan for complex network automation tasks. "
            "Use this when a request requires multiple coordinated actions."
        )

    @property
    def args_schema(self) -> type[BaseModel]:
        """Arguments schema."""
        return PlanInput

    def _execute_impl(self, request: str) -> str:
        """Generate execution plan for the request.

        Args:
            request: The user's request to plan for

        Returns:
            JSON string indicating plan should be generated
        """
        # The planner tool just marks that planning is needed
        # The actual planning happens in the planner node
        return f"Planning task: {request}"
