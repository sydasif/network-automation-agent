from langchain_core.tools import tool
from pydantic import BaseModel, Field


class NetworkResponse(BaseModel):
    """Structured response for network operations."""

    summary: str = Field(
        description="A human-readable summary highlighting operational status and anomalies. Use Markdown."
    )
    structured_data: dict | list = Field(
        description="The parsed data from the device output in JSON format (list or dict)."
    )
    errors: list[str] | None = Field(
        description="List of any errors encountered during execution."
    )


@tool(args_schema=NetworkResponse)
def respond(summary: str, structured_data: dict | list, errors: list[str] | None = None) -> str:
    """Provide the final response to the user.

    Call this tool when you have completed all network operations and want to report the results.
    Do NOT call this tool if you still have more commands to run.
    """
    return "Response delivered."
