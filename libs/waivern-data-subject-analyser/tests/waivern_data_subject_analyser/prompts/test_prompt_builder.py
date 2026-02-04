"""Tests for DataSubjectPromptBuilder.

Tests verify the PromptBuilder protocol implementation for data subject validation.
"""

import pytest
from waivern_core.schemas import BaseFindingEvidence, PatternMatchDetail

from waivern_data_subject_analyser.prompts.prompt_builder import (
    DataSubjectPromptBuilder,
)
from waivern_data_subject_analyser.schemas.types import (
    DataSubjectIndicatorMetadata,
    DataSubjectIndicatorModel,
)


def _make_finding(
    subject_category: str = "Customer",
    pattern: str = "customer_id",
) -> DataSubjectIndicatorModel:
    """Create a finding for testing."""
    return DataSubjectIndicatorModel(
        subject_category=subject_category,
        matched_patterns=[PatternMatchDetail(pattern=pattern, match_count=1)],
        confidence_score=80,
        evidence=[BaseFindingEvidence(content=f"Content: {pattern}")],
        metadata=DataSubjectIndicatorMetadata(source="test"),
    )


class TestDataSubjectPromptBuilder:
    """Test suite for DataSubjectPromptBuilder."""

    def test_build_prompt_includes_finding_ids_and_categories(self) -> None:
        """Prompt includes finding IDs and categories for response matching."""
        findings = [
            _make_finding("Customer", "customer_id"),
            _make_finding("Employee", "employee_id"),
        ]
        builder = DataSubjectPromptBuilder()

        prompt = builder.build_prompt(findings)

        # Finding IDs must be in prompt for response matching
        assert findings[0].id in prompt
        assert findings[1].id in prompt
        # Categories should be present
        assert "Customer" in prompt
        assert "Employee" in prompt

    def test_build_prompt_empty_findings_raises_error(self) -> None:
        """Empty findings list raises ValueError."""
        builder = DataSubjectPromptBuilder()

        with pytest.raises(ValueError, match="At least one finding"):
            builder.build_prompt([])

    def test_build_prompt_ignores_content_parameter(self) -> None:
        """Content parameter doesn't affect output (COUNT_BASED mode)."""
        finding = _make_finding("Customer", "customer_id")
        builder = DataSubjectPromptBuilder()

        prompt_without_content = builder.build_prompt([finding])
        prompt_with_content = builder.build_prompt(
            [finding], content="Some file content"
        )

        assert prompt_without_content == prompt_with_content
