"""JSON extraction utilities for LLM validation."""

import re


def extract_json_from_llm_response(llm_response: str) -> str:
    """Extract JSON from LLM response that may be wrapped in markdown.

    Claude often returns JSON wrapped in ```json``` blocks. This function
    extracts the clean JSON for parsing. Unified implementation that
    replaces duplicated functions in both personal data and processing
    purpose validation prompts.

    Args:
        llm_response: Raw response from LLM

    Returns:
        Clean JSON string

    Raises:
        ValueError: If no valid JSON found in response

    """
    # Remove markdown code block wrapper if present
    json_match = re.search(
        r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", llm_response, re.DOTALL
    )
    if json_match:
        return json_match.group(1).strip()

    # Look for array format directly
    array_match = re.search(r"\[.*?\]", llm_response, re.DOTALL)
    if array_match:
        return array_match.group(0).strip()

    # Look for object format directly
    obj_match = re.search(r"\{.*?\}", llm_response, re.DOTALL)
    if obj_match:
        return obj_match.group(0).strip()

    # If no JSON found, try to clean up the response
    cleaned = llm_response.strip()
    if cleaned.startswith(("[", "{")) and cleaned.endswith(("]", "}")):
        return cleaned

    raise ValueError("No valid JSON found in LLM response")
