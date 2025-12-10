"""Pydantic schemas for structured LLM outputs."""

from enum import Enum
from typing import Any, Dict, List, Optional

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


# --- New Planning Schemas ---


class ActionType(str, Enum):
    READ = "read"
    CONFIGURE = "configure"


class NetworkAction(BaseModel):
    """A single logical action to perform on a device."""

    action_type: ActionType = Field(
        description="Type of action: 'read' for show commands, 'configure' for config changes."
    )
    device: str = Field(description="The target device hostname.")
    command: str = Field(
        description="The full CLI command (e.g. 'show ver' or 'interface eth1\\n ip address...')."
    )


class ExecutionPlan(BaseModel):
    """The complete list of actions required to fulfill the user request."""

    steps: List[NetworkAction] = Field(
        default_factory=list,
        description="A list of sequential steps. Leave empty if no network actions are needed.",
    )
    direct_response: Optional[str] = Field(
        default=None,
        description="Use this field for general greetings, clarifications, or answers to non-network questions.",
    )
