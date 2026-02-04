"""Tests for RiskModifierPromptBuilder.

Tests verify the PromptBuilder protocol implementation for risk modifier detection.
Following the testing philosophy: test behaviour (input validation, protocol compliance),
not prompt content (which is configuration, not code).
"""

import pytest
from waivern_core.schemas import BaseFindingEvidence, PatternMatchDetail

from waivern_gdpr_data_subject_classifier.prompts.prompt_builder import (
    RiskModifierPromptBuilder,
)
from waivern_gdpr_data_subject_classifier.schemas import (
    GDPRDataSubjectFindingMetadata,
    GDPRDataSubjectFindingModel,
)


def _make_finding(
    data_subject_category: str = "customer",
    pattern: str = "customer_id",
) -> GDPRDataSubjectFindingModel:
    """Create a finding for testing."""
    return GDPRDataSubjectFindingModel(
        data_subject_category=data_subject_category,
        matched_patterns=[PatternMatchDetail(pattern=pattern, match_count=1)],
        confidence_score=80,
        evidence=[BaseFindingEvidence(content=f"Content: {pattern}")],
        metadata=GDPRDataSubjectFindingMetadata(source="test"),
    )


class TestRiskModifierPromptBuilder:
    """Test suite for RiskModifierPromptBuilder."""

    def test_build_prompt_empty_findings_raises_error(self) -> None:
        """Empty findings list raises ValueError."""
        builder = RiskModifierPromptBuilder(available_modifiers=[])

        with pytest.raises(ValueError, match="At least one finding"):
            builder.build_prompt([])

    def test_build_prompt_ignores_content_parameter(self) -> None:
        """Content parameter doesn't affect output (COUNT_BASED mode)."""
        finding = _make_finding("customer", "customer_id")
        builder = RiskModifierPromptBuilder(available_modifiers=[])

        prompt_without_content = builder.build_prompt([finding])
        prompt_with_content = builder.build_prompt(
            [finding], content="Some file content"
        )

        assert prompt_without_content == prompt_with_content

    def test_build_prompt_includes_finding_ids(self) -> None:
        """Prompt includes finding IDs for response matching."""
        findings = [
            _make_finding("customer", "customer_id"),
            _make_finding("employee", "employee_id"),
        ]
        builder = RiskModifierPromptBuilder(available_modifiers=[])

        prompt = builder.build_prompt(findings)

        # Finding IDs must be in prompt for response matching
        assert findings[0].id in prompt
        assert findings[1].id in prompt
