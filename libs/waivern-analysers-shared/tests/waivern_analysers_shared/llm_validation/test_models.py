"""Tests for shared LLM validation models - focuses on business-critical constraints."""

import pytest
from waivern_core.schemas import (
    BaseFindingEvidence,
    BaseFindingMetadata,
    BaseFindingModel,
    PatternMatchDetail,
)

from waivern_analysers_shared.llm_validation import LLMValidationResultModel


def _create_test_finding() -> BaseFindingModel[BaseFindingMetadata]:
    """Create a test finding with auto-generated UUID."""
    return BaseFindingModel(
        evidence=[BaseFindingEvidence(content="test content")],
        matched_patterns=[PatternMatchDetail(pattern="test_pattern", match_count=1)],
        metadata=BaseFindingMetadata(source="test_source"),
    )


class TestLLMValidationResultModel:
    """Test LLM validation result model - focuses on business-critical validation constraints."""

    def test_confidence_accepts_llm_output(self) -> None:
        """Test that confidence field accepts LLM output without range constraints.

        The ge/le constraints were removed because the Anthropic Batch API
        does not support minimum/maximum on number types in JSON Schema.
        LLM output is not reliably bounded, so validation is best-effort.
        """
        finding = _create_test_finding()

        result = LLMValidationResultModel(finding_id=finding.id, confidence=0.85)
        assert result.confidence == 0.85

        # Out-of-range values are accepted (LLM output is not reliably bounded)
        high = LLMValidationResultModel(finding_id=finding.id, confidence=1.5)
        assert high.confidence == 1.5

    def test_finding_id_must_be_non_empty(self) -> None:
        """Test that finding_id must be a non-empty string.

        Business requirement: Finding IDs must reference valid findings.
        Production impact: Empty IDs would fail to match any finding.
        """
        finding = _create_test_finding()

        # Valid ID should work - use actual finding.id (UUID)
        valid_result = LLMValidationResultModel(finding_id=finding.id)
        assert valid_result.finding_id == finding.id

        # Invalid ID - empty string
        with pytest.raises(ValueError):
            LLMValidationResultModel(finding_id="")
