"""Response tool for final user responses."""

from pydantic import BaseModel
from tools.base_tool import NetworkTool

class ResponseInput(BaseModel):
    """Input schema for responses. No arguments needed."""
    pass

class ResponseTool(NetworkTool):
    """Signal to format and display network data."""

    @property
    def name(self) -> str:
        return "final_response"

    @property
    def description(self) -> str:
        return "Use this ONLY when you have raw network data (from show_command) that needs to be formatted for the user."

    @property
    def args_schema(self) -> type[BaseModel]:
        return ResponseInput

    def _run(self) -> str:
        return "Routing to Response Node..."
