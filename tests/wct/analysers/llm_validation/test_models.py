"""Tests for shared LLM validation models - focuses on business-critical constraints."""

import pytest

from wct.analysers.llm_validation import LLMValidationResultModel


class TestLLMValidationResultModel:
    """Test LLM validation result model - focuses on business-critical validation constraints."""

    def test_confidence_bounds_prevent_data_corruption(self) -> None:
        """Test that confidence bounds prevent invalid data that would break downstream logic.

        Business requirement: Confidence scores must be 0.0-1.0 for proper risk assessment.
        Production impact: Invalid confidence scores break validation pipeline.
        """
        # Valid confidence range should work
        valid_result = LLMValidationResultModel(confidence=0.85)
        assert valid_result.confidence == 0.85

        # Invalid confidence - too high (prevents data corruption)
        with pytest.raises(ValueError):
            LLMValidationResultModel(confidence=1.5)

        # Invalid confidence - negative (prevents data corruption)
        with pytest.raises(ValueError):
            LLMValidationResultModel(confidence=-0.1)
