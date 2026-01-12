"""JSON extraction utilities for LLM validation."""

import re


def _find_balanced_json(
    text: str, start_pos: int, open_char: str, close_char: str
) -> str | None:
    """Find a balanced JSON structure starting at given position.

    Handles nested brackets and respects string boundaries (doesn't count
    brackets inside quoted strings).

    Args:
        text: The text to search in
        start_pos: Position of the opening bracket
        open_char: Opening bracket character ('[' or '{')
        close_char: Closing bracket character (']' or '}')

    Returns:
        The complete balanced JSON string, or None if not found

    """
    if start_pos >= len(text) or text[start_pos] != open_char:
        return None

    depth = 0
    in_string = False
    escape_next = False
    i = start_pos

    while i < len(text):
        char = text[i]

        if escape_next:
            escape_next = False
            i += 1
            continue

        if char == "\\":
            escape_next = True
            i += 1
            continue

        if char == '"':
            in_string = not in_string
            i += 1
            continue

        if not in_string:
            if char == open_char:
                depth += 1
            elif char == close_char:
                depth -= 1
                if depth == 0:
                    return text[start_pos : i + 1]

        i += 1

    return None  # Unbalanced


def extract_json_from_llm_response(llm_response: str) -> str:
    """Extract JSON from LLM response that may be wrapped in markdown.

    Claude often returns JSON wrapped in ```json``` blocks. This function
    extracts the clean JSON for parsing. Uses balanced bracket matching
    to correctly handle nested structures and brackets inside string values.

    Args:
        llm_response: Raw response from LLM

    Returns:
        Clean JSON string

    Raises:
        ValueError: If no valid JSON found in response

    """
    # First, try to extract from markdown code block
    # This is more reliable as the ``` boundaries are explicit
    code_block_match = re.search(r"```(?:json)?\s*", llm_response)
    if code_block_match:
        content_start = code_block_match.end()
        # Find the closing ```
        closing_match = re.search(r"```", llm_response[content_start:])
        if closing_match:
            block_content = llm_response[
                content_start : content_start + closing_match.start()
            ].strip()
            # The block content should be valid JSON - return it directly
            if block_content.startswith(("[", "{")):
                return block_content

    # Fallback: Find JSON structure using balanced bracket matching
    # Look for array first (more common in validation responses)
    for i, char in enumerate(llm_response):
        if char == "[":
            result = _find_balanced_json(llm_response, i, "[", "]")
            if result:
                return result.strip()
        elif char == "{":
            result = _find_balanced_json(llm_response, i, "{", "}")
            if result:
                return result.strip()

    # Last resort: check if the entire response is JSON
    cleaned = llm_response.strip()
    if cleaned.startswith(("[", "{")) and cleaned.endswith(("]", "}")):
        return cleaned

    raise ValueError("No valid JSON found in LLM response")
