"""Tests for shared LLM validation models - focuses on business-critical constraints."""

import pytest

from waivern_analysers_shared.llm_validation import LLMValidationResultModel


class TestLLMValidationResultModel:
    """Test LLM validation result model - focuses on business-critical validation constraints."""

    def test_confidence_bounds_prevent_data_corruption(self) -> None:
        """Test that confidence bounds prevent invalid data that would break downstream logic.

        Business requirement: Confidence scores must be 0.0-1.0 for proper risk assessment.
        Production impact: Invalid confidence scores break validation pipeline.
        """
        # Valid confidence range should work
        valid_result = LLMValidationResultModel(finding_index=0, confidence=0.85)
        assert valid_result.confidence == 0.85

        # Invalid confidence - too high (prevents data corruption)
        with pytest.raises(ValueError):
            LLMValidationResultModel(finding_index=0, confidence=1.5)

        # Invalid confidence - negative (prevents data corruption)
        with pytest.raises(ValueError):
            LLMValidationResultModel(finding_index=0, confidence=-0.1)

    def test_finding_index_must_be_non_negative(self) -> None:
        """Test that finding_index must be a non-negative integer.

        Business requirement: Finding indices must reference valid positions in finding lists.
        Production impact: Negative indices would cause incorrect finding matching.
        """
        # Valid index should work
        valid_result = LLMValidationResultModel(finding_index=0)
        assert valid_result.finding_index == 0

        valid_result = LLMValidationResultModel(finding_index=42)
        assert valid_result.finding_index == 42

        # Invalid index - negative (prevents incorrect finding matching)
        with pytest.raises(ValueError):
            LLMValidationResultModel(finding_index=-1)
