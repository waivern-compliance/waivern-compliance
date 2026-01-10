"""Tests for shared LLM validation models - focuses on business-critical constraints."""

import pytest
from waivern_core.schemas import BaseFindingEvidence, BaseFindingModel

from waivern_analysers_shared.llm_validation import LLMValidationResultModel


def _create_test_finding() -> BaseFindingModel:
    """Create a test finding with auto-generated UUID."""
    return BaseFindingModel(
        evidence=[BaseFindingEvidence(content="test content")],
        matched_patterns=["test_pattern"],
    )


class TestLLMValidationResultModel:
    """Test LLM validation result model - focuses on business-critical validation constraints."""

    def test_confidence_bounds_prevent_data_corruption(self) -> None:
        """Test that confidence bounds prevent invalid data that would break downstream logic.

        Business requirement: Confidence scores must be 0.0-1.0 for proper risk assessment.
        Production impact: Invalid confidence scores break validation pipeline.
        """
        finding = _create_test_finding()

        # Valid confidence range should work
        valid_result = LLMValidationResultModel(finding_id=finding.id, confidence=0.85)
        assert valid_result.confidence == 0.85

        # Invalid confidence - too high (prevents data corruption)
        with pytest.raises(ValueError):
            LLMValidationResultModel(finding_id=finding.id, confidence=1.5)

        # Invalid confidence - negative (prevents data corruption)
        with pytest.raises(ValueError):
            LLMValidationResultModel(finding_id=finding.id, confidence=-0.1)

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
