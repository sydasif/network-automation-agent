"""Helper utilities for LLM operations.

This module provides utility functions for working with LLM responses,
particularly for Groq API compatibility.
"""

import json
import logging
import re
from typing import Any

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


def parse_json_from_llm_response(response_text: str) -> dict[str, Any]:
    """Parse JSON from LLM response with multiple fallback strategies.

    This function handles various formats that LLMs might return:
    1. Direct JSON response
    2. JSON wrapped in markdown code blocks
    3. JSON embedded in text

    Args:
        response_text: Raw text response from LLM

    Returns:
        Parsed JSON as dictionary

    Raises:
        ValueError: If no valid JSON found in response
    """
    # First try: parse whole response as JSON
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # Second try: find JSON in markdown code blocks
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Third try: find JSON object in text
    json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"No valid JSON found in response: {response_text[:200]}...")


def get_structured_response(
    llm,
    prompt: str,
    schema: type[BaseModel],
    json_instruction: str | None = None,
) -> BaseModel:
    """Get structured response from LLM using manual JSON parsing.

    This is a Groq-compatible alternative to `with_structured_output()`.

    Args:
        llm: LLM instance
        prompt: Prompt to send to LLM
        schema: Pydantic model to validate response against
        json_instruction: Optional custom JSON format instruction.
                         If None, uses a default based on schema.

    Returns:
        Validated Pydantic model instance

    Raises:
        ValueError: If response doesn't match schema
        ValidationError: If Pydantic validation fails

    Example:
        ```python
        from pydantic import BaseModel, Field

        class MyResponse(BaseModel):
            answer: str = Field(description="The answer")
            confidence: float = Field(description="Confidence 0-1")

        llm = self._get_llm()
        result = get_structured_response(
            llm,
            "What is 2+2?",
            MyResponse
        )
        print(result.answer)  # Access validated fields
        ```
    """
    # Add JSON format instruction if not provided
    if json_instruction is None:
        # Generate instruction from schema
        schema_json = schema.model_json_schema()
        properties = schema_json.get("properties", {})

        json_instruction = (
            f"\n\nReturn your response as a JSON object with this exact format:\n"
            f"{json.dumps({k: f'<{v.get("description", k)}>' for k, v in properties.items()}, indent=2)}"
        )

    full_prompt = prompt + json_instruction

    # Invoke LLM
    response = llm.invoke(full_prompt)
    response_text = response.content

    # Parse JSON from response
    parsed = parse_json_from_llm_response(response_text)

    # Validate against schema
    try:
        return schema(**parsed)
    except ValidationError as e:
        logger.error(f"Schema validation failed: {e}")
        raise ValueError(f"Response doesn't match expected schema: {e}") from e
