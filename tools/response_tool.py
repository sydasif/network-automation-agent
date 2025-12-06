"""Response tool for final user responses.

This module provides the ResponseTool class for formatting
and returning final responses to users.
"""

from pydantic import BaseModel, Field

from tools.base_tool import NetworkTool


class ResponseInput(BaseModel):
    """Input schema for responses."""

    message: str = Field(description="The response message to send to the user.")


class ResponseTool(NetworkTool):
    """Send final response to the user.

    This tool is used to format and return the final response
    to the user after all tasks are complete.
    """

    @property
    def name(self) -> str:
        """Tool name."""
        return "respond"

    @property
    def description(self) -> str:
        """Tool description."""
        return "Send final response to user. Call ONLY when task complete."

    @property
    def args_schema(self) -> type[BaseModel]:
        """Arguments schema."""
        return ResponseInput

    def _run(self, message: str) -> str:
        """Return the response message.

        Args:
            message: The response message

        Returns:
            The response message
        """
        return message
