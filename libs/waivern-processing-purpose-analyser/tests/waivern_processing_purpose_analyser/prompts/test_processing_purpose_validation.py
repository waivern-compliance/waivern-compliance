"""Tests for processing purpose validation prompts focusing on behaviour."""

import pytest
from waivern_core.schemas import BaseFindingEvidence

from waivern_processing_purpose_analyser.prompts.processing_purpose_validation import (
    get_processing_purpose_validation_prompt,
)
from waivern_processing_purpose_analyser.schemas.types import (
    ProcessingPurposeFindingMetadata,
    ProcessingPurposeFindingModel,
)


class TestProcessingPurposeValidationPrompt:
    """Test processing purpose validation prompt generation focusing on behaviour."""

    def create_test_finding(
        self,
        purpose: str = "Test Purpose",
        purpose_category: str = "OPERATIONAL",
        matched_pattern: str = "test",
        evidence: list[str] | None = None,
        source: str = "test_source",
    ) -> ProcessingPurposeFindingModel:
        """Helper to create test finding objects."""
        evidence_list = evidence if evidence is not None else ["test evidence"]
        evidence_items = [
            BaseFindingEvidence(content=content)  # collection_timestamp has default
            for content in evidence_list
        ]
        metadata = ProcessingPurposeFindingMetadata(source=source)

        return ProcessingPurposeFindingModel(
            purpose=purpose,
            purpose_category=purpose_category,
            matched_patterns=[matched_pattern],
            evidence=evidence_items,
            metadata=metadata,
        )

    def test_get_processing_purpose_validation_prompt_basic_functionality(self) -> None:
        """Test that prompt generation works with basic finding data."""
        # Arrange
        findings = [
            self.create_test_finding(
                purpose="Customer Service",
                purpose_category="OPERATIONAL",
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
        findings = [self.create_test_finding()]

        # Act
        prompt = get_processing_purpose_validation_prompt(findings, "conservative")

        # Assert - Conservative mode should offer flag_for_review option
        assert '"flag_for_review"' in prompt

    def test_standard_mode_excludes_flag_for_review_option(self) -> None:
        """Test that standard mode does not include flag_for_review action option."""
        # Arrange
        findings = [self.create_test_finding()]

        # Act
        prompt = get_processing_purpose_validation_prompt(findings, "standard")

        # Assert - Standard mode should not offer flag_for_review option
        assert '"flag_for_review"' not in prompt

    def test_privacy_sensitive_categories_trigger_warnings(self) -> None:
        """Test that privacy-sensitive categories trigger warnings when explicitly configured."""
        sensitive_categories = ["AI_AND_ML", "ANALYTICS", "MARKETING_AND_ADVERTISING"]

        for category in sensitive_categories:
            # Arrange
            findings = [
                self.create_test_finding(
                    purpose_category=category,
                )
            ]

            # Act - Pass sensitive categories explicitly
            prompt = get_processing_purpose_validation_prompt(
                findings, "conservative", sensitive_categories
            )

            # Assert
            assert "PRIVACY SENSITIVE" in prompt, (
                f"Category {category} should trigger privacy warning when configured"
            )

    def test_security_category_does_not_trigger_privacy_warnings(self) -> None:
        """Test that security category alone doesn't trigger privacy-sensitive warnings."""
        # Arrange
        findings = [
            self.create_test_finding(
                purpose="Security",
                purpose_category="SECURITY",
                matched_pattern="security",
            )
        ]
        # Define which categories are privacy-sensitive (does not include SECURITY)
        sensitive_categories = ["AI_AND_ML", "ANALYTICS", "MARKETING_AND_ADVERTISING"]

        # Act
        prompt = get_processing_purpose_validation_prompt(
            findings, "conservative", sensitive_categories
        )

        # Assert - SECURITY is not in the sensitive categories list
        assert "PRIVACY SENSITIVE" not in prompt

    def test_always_uses_array_response_format(self) -> None:
        """Test that response format is always array-based for consistency."""
        # Test single finding
        single_finding = [self.create_test_finding()]
        prompt_single = get_processing_purpose_validation_prompt(
            single_finding, "standard"
        )

        # Test multiple findings
        multiple_findings = [self.create_test_finding(), self.create_test_finding()]
        prompt_multiple = get_processing_purpose_validation_prompt(
            multiple_findings, "standard"
        )

        # Both should use array format with finding_id (UUID)
        assert '"finding_id":' in prompt_single
        assert '"finding_id":' in prompt_multiple
        # Prompt should ask for only FALSE_POSITIVE results
        assert "Return ONLY the FALSE_POSITIVE" in prompt_single
        assert "Review all 1 findings" in prompt_single
        assert "Review all 2 findings" in prompt_multiple

    def test_conservative_mode_extends_reasoning_length(self) -> None:
        """Test that conservative mode allows longer reasoning explanations."""
        # Arrange
        findings = [self.create_test_finding()]

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
            self.create_test_finding(
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
        """Test that invalid validation modes fall back to standard behaviour."""
        # Arrange
        findings = [self.create_test_finding()]

        # Act
        prompt = get_processing_purpose_validation_prompt(findings, "invalid_mode")

        # Assert - Should fall back to standard mode behaviour
        assert "STANDARD VALIDATION MODE" in prompt
        assert "CONSERVATIVE VALIDATION MODE" not in prompt
        assert '"flag_for_review"' not in prompt
