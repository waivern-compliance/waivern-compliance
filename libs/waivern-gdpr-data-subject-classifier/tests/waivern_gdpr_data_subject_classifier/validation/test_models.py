"""Tests for risk modifier validation models - focuses on business-critical constraints."""

import pytest

from waivern_gdpr_data_subject_classifier.validation.models import (
    RiskModifierResultModel,
)


class TestRiskModifierResultModel:
    """Test risk modifier result model - focuses on business-critical validation constraints."""

    def test_confidence_bounds_reject_invalid_values(self) -> None:
        """Test that confidence outside 0.0-1.0 is rejected.

        Business requirement: Confidence scores must be 0.0-1.0 for proper risk assessment.
        Production impact: Invalid confidence scores break validation pipeline.
        """
        # Valid confidence should work
        valid_result = RiskModifierResultModel(
            finding_id="test-finding-id",
            risk_modifiers=["minor"],
            confidence=0.85,
        )
        assert valid_result.confidence == 0.85

        # Invalid confidence - too high
        with pytest.raises(ValueError):
            RiskModifierResultModel(
                finding_id="test-finding-id",
                risk_modifiers=[],
                confidence=1.5,
            )

        # Invalid confidence - negative
        with pytest.raises(ValueError):
            RiskModifierResultModel(
                finding_id="test-finding-id",
                risk_modifiers=[],
                confidence=-0.1,
            )

    def test_finding_id_must_be_non_empty(self) -> None:
        """Test that finding_id must be a non-empty string.

        Business requirement: Finding IDs must reference valid findings.
        Production impact: Empty IDs would fail to match any finding.
        """
        # Valid ID should work
        valid_result = RiskModifierResultModel(
            finding_id="valid-finding-id",
            risk_modifiers=[],
        )
        assert valid_result.finding_id == "valid-finding-id"

        # Invalid ID - empty string
        with pytest.raises(ValueError):
            RiskModifierResultModel(
                finding_id="",
                risk_modifiers=[],
            )

    def test_empty_risk_modifiers_list_is_valid(self) -> None:
        """Test that empty risk_modifiers list is accepted.

        Business requirement: Not all findings have risk modifiers.
        Production impact: Valid findings without modifiers should not fail validation.
        """
        result = RiskModifierResultModel(
            finding_id="test-finding-id",
            risk_modifiers=[],
        )

        assert result.risk_modifiers == []
        assert result.reasoning == "No risk modifiers detected"  # Default value
