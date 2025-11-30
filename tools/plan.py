from langchain_core.tools import tool
from pydantic import BaseModel, Field


class PlanInput(BaseModel):
    """Input for the planning tool."""

    request: str = Field(description="The complex request that needs planning.")


@tool(args_schema=PlanInput)
def plan_task(request: str) -> str:
    """Create a detailed plan for a complex network task.

    Use this tool when the user asks for a high-level objective that requires multiple steps,
    such as 'upgrade all switches', 'troubleshoot connectivity', or 'audit security'.
    """
    return "Planning..."
