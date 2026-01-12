"""Tests for shared JSON extraction utilities."""

import pytest

from waivern_analysers_shared.llm_validation.json_utils import (
    extract_json_from_llm_response,
)


class TestExtractJsonFromLlmResponse:
    """Test JSON extraction from LLM responses."""

    def test_handles_all_json_formats_with_surrounding_text(self) -> None:
        """Test comprehensive JSON extraction from all LLM response formats."""
        # Test markdown JSON block (preferred format)
        markdown_response = """Here is the analysis:
        ```json
        {"test": "markdown_value"}
        ```
        Analysis complete."""
        result = extract_json_from_llm_response(markdown_response)
        assert result == '{"test": "markdown_value"}'

        # Test generic markdown block
        generic_block = """Analysis result:
        ```
        [{"finding_id": "abc-123", "result": "TRUE_POSITIVE"}]
        ```"""
        result = extract_json_from_llm_response(generic_block)
        assert result == '[{"finding_id": "abc-123", "result": "TRUE_POSITIVE"}]'

        # Test direct JSON object with text
        direct_object = """The validation result is:
        {"validation_result": "TRUE_POSITIVE", "confidence": 0.95}
        End of analysis."""
        result = extract_json_from_llm_response(direct_object)
        assert result == '{"validation_result": "TRUE_POSITIVE", "confidence": 0.95}'

        # Test direct JSON array with whitespace
        array_with_space = """
        [{"test": "array_value"}, {"test": "value2"}]
        """
        result = extract_json_from_llm_response(array_with_space)
        assert result == '[{"test": "array_value"}, {"test": "value2"}]'

    def test_raises_error_on_no_json(self) -> None:
        """Test that ValueError is raised when no JSON is found."""
        response = "This is just plain text with no JSON content."

        with pytest.raises(ValueError, match="No valid JSON found"):
            extract_json_from_llm_response(response)

    def test_raises_error_on_empty_response(self) -> None:
        """Test that ValueError is raised on empty response."""
        with pytest.raises(ValueError, match="No valid JSON found"):
            extract_json_from_llm_response("")

    def test_handles_brackets_inside_string_values(self) -> None:
        """Test extraction when JSON string values contain bracket characters.

        This is critical for LLM validation where reasoning text may reference
        arrays, data structures, or use bracket notation like [email] or [data].
        """
        # Array with brackets inside string values
        response_with_brackets = """```json
[
  {
    "finding_id": "abc-123",
    "validation_result": "FALSE_POSITIVE",
    "reasoning": "Email data [structure] for rate limiting is security, not customer service."
  },
  {
    "finding_id": "def-456",
    "validation_result": "TRUE_POSITIVE",
    "reasoning": "This handles user [profile] data for account management."
  }
]
```"""
        result = extract_json_from_llm_response(response_with_brackets)
        # Should extract the FULL array, not truncate at first ]
        assert result.startswith("[")
        assert result.endswith("]")
        assert "abc-123" in result
        assert "def-456" in result  # Must include second object
        assert "Email data [structure]" in result

    def test_handles_nested_arrays_in_json(self) -> None:
        """Test extraction of JSON with nested array structures."""
        response_with_nested = """Here is the result:
[
  {"id": "1", "tags": ["a", "b", "c"]},
  {"id": "2", "tags": ["x", "y"]}
]
Done."""
        result = extract_json_from_llm_response(response_with_nested)
        assert result.startswith("[")
        assert result.endswith("]")
        assert '"id": "2"' in result  # Must include second object
