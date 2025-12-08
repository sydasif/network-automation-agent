"""Pydantic schemas for structured LLM outputs."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentResponse(BaseModel):
    """The structured final response from the Network Agent."""

    summary: str = Field(
        description="A concise, natural language summary of the execution results for the user."
    )
    structured_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="The normalized raw data extracted from the tool output (if any).",
    )
    error: Optional[str] = Field(
        default=None,
        description="If the execution failed, a user-friendly error message.",
    )
    suggested_next_steps: List[str] = Field(
        default_factory=list,
        description="A list of 1-3 short follow-up commands the user might want to run.",
    )