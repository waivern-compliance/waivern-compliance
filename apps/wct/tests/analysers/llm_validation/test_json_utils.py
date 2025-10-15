"""Tests for shared JSON extraction utilities."""

import pytest

from wct.analysers.llm_validation.json_utils import extract_json_from_llm_response


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
        [{"finding_index": 0, "result": "TRUE_POSITIVE"}]
        ```"""
        result = extract_json_from_llm_response(generic_block)
        assert result == '[{"finding_index": 0, "result": "TRUE_POSITIVE"}]'

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
