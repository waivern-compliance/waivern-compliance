"""Tests for ProcessingPurposePromptBuilder.

Tests verify the PromptBuilder protocol implementation for processing purpose validation.
"""

import pytest
from waivern_core.schemas import BaseFindingEvidence, PatternMatchDetail

from waivern_processing_purpose_analyser.prompts.prompt_builder import (
    ProcessingPurposePromptBuilder,
)
from waivern_processing_purpose_analyser.schemas.types import (
    ProcessingPurposeIndicatorMetadata,
    ProcessingPurposeIndicatorModel,
)


def _make_finding(
    purpose: str = "Payment Processing",
    pattern: str = "payment",
    source: str = "test_source",
) -> ProcessingPurposeIndicatorModel:
    """Create a finding for testing."""
    return ProcessingPurposeIndicatorModel(
        purpose=purpose,
        matched_patterns=[PatternMatchDetail(pattern=pattern, match_count=1)],
        evidence=[BaseFindingEvidence(content=f"Content: {pattern}")],
        metadata=ProcessingPurposeIndicatorMetadata(source=source),
    )


class TestProcessingPurposePromptBuilder:
    """Test suite for ProcessingPurposePromptBuilder."""

    def test_build_prompt_includes_finding_ids_and_purposes(self) -> None:
        """Prompt includes finding IDs and purposes for response matching."""
        findings = [
            _make_finding("Payment Processing", "payment"),
            _make_finding("User Analytics", "analytics"),
        ]
        builder = ProcessingPurposePromptBuilder()

        prompt = builder.build_prompt(findings)

        # Finding IDs must be in prompt for response matching
        assert findings[0].id in prompt
        assert findings[1].id in prompt
        # Purposes should be present
        assert "Payment Processing" in prompt
        assert "User Analytics" in prompt

    def test_build_prompt_empty_findings_raises_error(self) -> None:
        """Empty findings list raises ValueError."""
        builder = ProcessingPurposePromptBuilder()

        with pytest.raises(ValueError, match="At least one finding"):
            builder.build_prompt([])

    def test_build_prompt_ignores_content_parameter(self) -> None:
        """Content parameter doesn't affect output (COUNT_BASED mode)."""
        finding = _make_finding("Payment Processing", "payment")
        builder = ProcessingPurposePromptBuilder()

        prompt_without_content = builder.build_prompt([finding])
        prompt_with_content = builder.build_prompt(
            [finding], content="Some file content that should be ignored"
        )

        assert prompt_without_content == prompt_with_content
