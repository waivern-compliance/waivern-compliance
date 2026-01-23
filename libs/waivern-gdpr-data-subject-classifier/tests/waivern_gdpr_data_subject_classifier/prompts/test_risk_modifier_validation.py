"""Tests for risk modifier validation prompt."""

import pytest

from waivern_gdpr_data_subject_classifier.prompts import (
    get_risk_modifier_validation_prompt,
)


class TestRiskModifierValidationPrompt:
    """Test risk modifier validation prompt generation."""

    def test_empty_findings_raises_error(self) -> None:
        """Test that empty findings list raises ValueError.

        Defensive check - no point calling LLM with no findings to analyse.
        """
        with pytest.raises(ValueError, match="At least one finding must be provided"):
            get_risk_modifier_validation_prompt(findings=[], available_modifiers=[])
