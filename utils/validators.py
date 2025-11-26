"""Reusable Pydantic validators for tool arguments."""

from typing import Annotated, Any

from pydantic import BeforeValidator


def _ensure_list(v: Any) -> list[str]:
    """Coerce string input to a list of strings."""
    if isinstance(v, str):
        return [v]
    return v


# MAGIC TYPE:
# 1. The LLM sees: list[str] (Forces it to try and output a list)
# 2. The Code accepts: str OR list (Handles it if the LLM fails and sends a string)
FlexibleList = Annotated[list[str], BeforeValidator(_ensure_list)]
