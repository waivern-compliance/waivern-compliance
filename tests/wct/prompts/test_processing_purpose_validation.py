"""Tests for processing purpose validation prompts focusing on behavior."""

import pytest

from wct.analysers.processing_purpose_analyser.types import (
    ProcessingPurposeFindingMetadata,
    ProcessingPurposeFindingModel,
)
from wct.analysers.types import EvidenceItem
from wct.prompts.processing_purpose_validation import (
    RecommendedAction,
    ValidationResult,
    extract_json_from_response,
    get_processing_purpose_validation_prompt,
)


class TestProcessingPurposeValidationPrompt:
    """Test processing purpose validation prompt generation focusing on behavior."""

    def _create_test_finding(
        self,
        purpose: str = "Test Purpose",
        purpose_category: str = "OPERATIONAL",
        risk_level: str = "low",
        matched_pattern: str = "test",
        **kwargs,
    ) -> ProcessingPurposeFindingModel:
        """Helper to create test finding objects."""
        evidence = kwargs.get("evidence", ["test evidence"])
        source = kwargs.get("source", "test_source")

        evidence_items = [
            EvidenceItem(content=content)  # collection_timestamp has default
            for content in (evidence or ["test evidence"])
        ]
        metadata = ProcessingPurposeFindingMetadata(source=source) if source else None

        return ProcessingPurposeFindingModel(
            purpose=purpose,
            purpose_category=purpose_category,
            risk_level=risk_level,
            matched_pattern=matched_pattern,
            evidence=evidence_items,
            metadata=metadata,
        )

    def test_get_processing_purpose_validation_prompt_basic_functionality(self) -> None:
        """Test that prompt generation works with basic finding data."""
        # Arrange
        findings = [
            self._create_test_finding(
                purpose="Customer Service",
                purpose_category="OPERATIONAL",
                risk_level="low",
                matched_pattern="zendesk",
                evidence=["zendesk ticket system"],
                source="database",
            )
        ]

        # Act
        prompt = get_processing_purpose_validation_prompt(findings, "standard")

        # Assert - Test basic functionality
        assert isinstance(prompt, str)
        assert len(prompt) > 100  # Should be substantial

        # Test that finding data is properly injected
        assert "Customer Service" in prompt
        assert "OPERATIONAL" in prompt
        assert "zendesk" in prompt
        assert "zendesk ticket system" in prompt

    def test_conservative_mode_enables_flag_for_review_option(self) -> None:
        """Test that conservative mode includes flag_for_review action option."""
        # Arrange
        findings = [self._create_test_finding()]

        # Act
        prompt = get_processing_purpose_validation_prompt(findings, "conservative")

        # Assert - Conservative mode should offer flag_for_review option
        assert '"flag_for_review"' in prompt

    def test_standard_mode_excludes_flag_for_review_option(self) -> None:
        """Test that standard mode does not include flag_for_review action option."""
        # Arrange
        findings = [self._create_test_finding()]

        # Act
        prompt = get_processing_purpose_validation_prompt(findings, "standard")

        # Assert - Standard mode should not offer flag_for_review option
        assert '"flag_for_review"' not in prompt

    def test_high_risk_findings_trigger_conservative_warnings(self) -> None:
        """Test that high-risk findings trigger appropriate warnings in conservative mode."""
        # Arrange
        high_risk_findings = [
            self._create_test_finding(
                purpose="AI Training",
                purpose_category="AI_AND_ML",
                risk_level="high",
                matched_pattern="ml",
            )
        ]

        # Act
        prompt = get_processing_purpose_validation_prompt(
            high_risk_findings, "conservative"
        )

        # Assert - Should warn about high-risk processing
        assert "HIGH RISK PROCESSING" in prompt

    def test_privacy_sensitive_categories_trigger_warnings(self) -> None:
        """Test that privacy-sensitive categories trigger warnings in conservative mode."""
        sensitive_categories = ["AI_AND_ML", "ANALYTICS", "MARKETING_AND_ADVERTISING"]

        for category in sensitive_categories:
            # Arrange
            findings = [
                self._create_test_finding(
                    purpose_category=category,
                    risk_level="medium",
                )
            ]

            # Act
            prompt = get_processing_purpose_validation_prompt(findings, "conservative")

            # Assert
            assert "PRIVACY SENSITIVE" in prompt, (
                f"Category {category} should trigger privacy warning"
            )

    def test_security_category_does_not_trigger_privacy_warnings(self) -> None:
        """Test that security category alone doesn't trigger privacy-sensitive warnings."""
        # Arrange
        findings = [
            self._create_test_finding(
                purpose="Security",
                purpose_category="SECURITY",
                risk_level="high",
                matched_pattern="security",
            )
        ]

        # Act
        prompt = get_processing_purpose_validation_prompt(findings, "conservative")

        # Assert - Should trigger high-risk but not privacy-sensitive warnings
        assert "HIGH RISK PROCESSING" in prompt  # Due to high risk level
        assert "PRIVACY SENSITIVE" not in prompt  # Security not privacy-sensitive

    def test_always_uses_array_response_format(self) -> None:
        """Test that response format is always array-based for consistency."""
        # Test single finding
        single_finding = [self._create_test_finding()]
        prompt_single = get_processing_purpose_validation_prompt(
            single_finding, "standard"
        )

        # Test multiple findings
        multiple_findings = [self._create_test_finding(), self._create_test_finding()]
        prompt_multiple = get_processing_purpose_validation_prompt(
            multiple_findings, "standard"
        )

        # Both should use array format
        assert '"finding_index": 0,' in prompt_single
        assert '"finding_index": 0,' in prompt_multiple
        assert "return array with 1 element(s)" in prompt_single
        assert "return array with 2 element(s)" in prompt_multiple

    def test_conservative_mode_extends_reasoning_length(self) -> None:
        """Test that conservative mode allows longer reasoning explanations."""
        # Arrange
        findings = [self._create_test_finding()]

        # Act
        standard_prompt = get_processing_purpose_validation_prompt(findings, "standard")
        conservative_prompt = get_processing_purpose_validation_prompt(
            findings, "conservative"
        )

        # Assert - Conservative mode should allow longer reasoning
        assert "max 120 words" in standard_prompt
        assert "max 150 words" in conservative_prompt

    def test_evidence_formatting(self) -> None:
        """Test that evidence is properly formatted in the prompt."""
        # Arrange
        findings = [
            self._create_test_finding(
                evidence=["evidence 1", "evidence 2", "evidence 3"]
            )
        ]

        # Act
        prompt = get_processing_purpose_validation_prompt(findings, "standard")

        # Assert - Evidence should be formatted as list items
        assert "- evidence 1" in prompt
        assert "- evidence 2" in prompt
        assert "- evidence 3" in prompt

    def test_error_handling(self) -> None:
        """Test error handling for invalid inputs."""
        # Test empty findings list
        with pytest.raises(ValueError, match="At least one finding must be provided"):
            get_processing_purpose_validation_prompt([], "standard")

    def test_validation_mode_fallback(self) -> None:
        """Test that invalid validation modes fall back to standard behavior."""
        # Arrange
        findings = [self._create_test_finding()]

        # Act
        prompt = get_processing_purpose_validation_prompt(findings, "invalid_mode")

        # Assert - Should fall back to standard mode behavior
        assert "STANDARD VALIDATION MODE" in prompt
        assert "CONSERVATIVE VALIDATION MODE" not in prompt
        assert '"flag_for_review"' not in prompt


class TestExtractJsonFromResponse:
    """Test JSON extraction utility function."""

    def test_extract_json_from_response_with_markdown_wrapper(self) -> None:
        """Test JSON extraction from markdown-wrapped response."""
        # Arrange
        llm_response = """Here's my analysis:

```json
{
  "validation_result": "TRUE_POSITIVE",
  "confidence": 0.85,
  "reasoning": "This appears to be actual business processing",
  "recommended_action": "keep"
}
```

That's my assessment."""

        # Act
        result = extract_json_from_response(llm_response)

        # Assert
        expected = """{
  "validation_result": "TRUE_POSITIVE",
  "confidence": 0.85,
  "reasoning": "This appears to be actual business processing",
  "recommended_action": "keep"
}"""
        assert result == expected

    def test_extract_json_from_response_with_array(self) -> None:
        """Test JSON array extraction from markdown-wrapped response."""
        # Arrange
        llm_response = """```json
[
  {
    "finding_index": 0,
    "validation_result": "TRUE_POSITIVE",
    "confidence": 0.9
  }
]
```"""

        # Act
        result = extract_json_from_response(llm_response)

        # Assert
        expected = """[
  {
    "finding_index": 0,
    "validation_result": "TRUE_POSITIVE",
    "confidence": 0.9
  }
]"""
        assert result == expected

    def test_extract_json_from_response_plain_json(self) -> None:
        """Test JSON extraction from plain response without markdown."""
        # Arrange
        plain_json = '{"validation_result": "FALSE_POSITIVE", "confidence": 0.95}'

        # Act
        result = extract_json_from_response(plain_json)

        # Assert
        assert result == plain_json

    def test_extract_json_from_response_no_json_format(self) -> None:
        """Test extraction when response contains no JSON formatting."""
        # Arrange
        text_response = "This is just plain text with no JSON."

        # Act
        result = extract_json_from_response(text_response)

        # Assert
        assert result == text_response

    def test_extract_json_from_response_with_json_lang_specifier(self) -> None:
        """Test JSON extraction with explicit json language specifier."""
        # Arrange
        llm_response = """```json
[{"finding_index": 0, "validation_result": "FALSE_POSITIVE"}]
```"""

        # Act
        result = extract_json_from_response(llm_response)

        # Assert
        assert result == '[{"finding_index": 0, "validation_result": "FALSE_POSITIVE"}]'


class TestValidationConstants:
    """Test validation result and action constants."""

    def test_validation_result_constants(self) -> None:
        """Test ValidationResult constants are properly defined."""
        # Assert
        assert ValidationResult.TRUE_POSITIVE == "TRUE_POSITIVE"
        assert ValidationResult.FALSE_POSITIVE == "FALSE_POSITIVE"

    def test_recommended_action_constants(self) -> None:
        """Test RecommendedAction constants are properly defined."""
        # Assert
        assert RecommendedAction.KEEP == "keep"
        assert RecommendedAction.DISCARD == "discard"
        assert RecommendedAction.FLAG_FOR_REVIEW == "flag_for_review"
