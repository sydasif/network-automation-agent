"""Multi-command tool for complex network automation tasks.

This module provides the MultiCommandTool class for breaking down
complex requests into step-by-step execution plans.
"""

from pydantic import BaseModel, Field

from tools.base_tool import NetworkTool


class MultiCommandInput(BaseModel):
    """Input schema for multi-command tasks."""

    request: str = Field(description="User request to create a plan for")


class MultiCommandTool(NetworkTool):
    """Generate step-by-step execution plans for complex requests.

    This tool analyzes complex network automation requests and breaks
    them down into logical, sequential steps.
    """

    @property
    def name(self) -> str:
        """Tool name."""
        return "multi_command"

    @property
    def description(self) -> str:
        """Tool description."""
        return (
            "Plan complex multi-step/multi-device operations. "
            "Use for: coordination, verification steps, troubleshooting sequences. "
        )

    @property
    def args_schema(self) -> type[BaseModel]:
        """Arguments schema."""
        return MultiCommandInput

    def _run(self, request: str) -> str:
        """Generate execution plan for the request.

        Args:
            request: The user's request to plan for

        Returns:
            JSON string indicating plan should be generated
        """
        # The planner tool just marks that planning is needed
        # The actual planning happens in the planner node
        return f"Planning task: {request}"
