"""Format output tool for structured LLM responses.

This module provides the FormatOutputTool class that allows the LLM
to return structured network data via tool calling instead of manual JSON parsing.
"""

import json

from pydantic import BaseModel, Field

from tools.base_tool import NetworkTool


class FormatOutputInput(BaseModel):
    """Input schema for format_output tool."""

    summary: str = Field(
        description="Human-readable summary highlighting operational status, health, and anomalies. Use Markdown for readability."
    )
    structured_data: dict | list = Field(
        description="The parsed data from device output as a dictionary or list."
    )
    errors: list[str] | None = Field(
        default=None,
        description="List of any errors encountered during execution (or null if none).",
    )


class FormatOutputTool(NetworkTool):
    """Format tool outputs into structured responses.

    This tool allows the LLM to return structured data via tool calling,
    avoiding Groq API issues with with_structured_output().
    """

    @property
    def name(self) -> str:
        """Tool name."""
        return "format_output"

    @property
    def description(self) -> str:
        """Tool description."""
        return (
            "Format network command output into structured JSON response. "
            "Use this tool to return the final formatted output to the user. "
            "Provide a human-readable summary, structured data (parsed from device output), "
            "and any errors encountered. "
            "This is the FINAL step - call this tool to complete the request."
        )

    @property
    def args_schema(self) -> type[BaseModel]:
        """Arguments schema."""
        return FormatOutputInput

    def _run(
        self, summary: str, structured_data: dict | list, errors: list[str] | None = None
    ) -> str:
        """Format output into structured response.

        Args:
            summary: Human-readable summary
            structured_data: Parsed data as dict or list
            errors: Optional list of errors

        Returns:
            JSON string with formatted response
        """
        response = {
            "summary": summary,
            "structured_data": structured_data,
            "errors": errors or [],
        }

        return json.dumps(response, indent=2)
