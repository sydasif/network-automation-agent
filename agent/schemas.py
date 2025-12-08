"""Pydantic schemas for structured LLM outputs."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AgentResponse(BaseModel):
    """The structured final response from the Network Agent."""

    summary: str = Field(
        description=(
            "A professional network engineering summary in strictly formatted Markdown. "
            "MUST use Level 3 Headings (###) for sections. "
            "MUST use Markdown Tables for data presentation where possible. "
            "MUST use Bullet points for lists."
        )
    )
    structured_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="The normalized raw data extracted from the tool output (if any).",
    )
    error: Optional[str] = Field(
        default=None,
        description="If the execution failed, a user-friendly error message.",
    )
