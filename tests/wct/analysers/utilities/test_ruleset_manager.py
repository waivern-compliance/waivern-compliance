"""Tests for RulesetManager utility."""

from unittest.mock import patch

import pytest

from wct.analysers.utilities import RulesetManager
from wct.rulesets.types import ProcessingPurposeRule


class TestRulesetManager:
    """Test suite for RulesetManager utility class."""

    def test_get_rules_loads_ruleset_successfully(self) -> None:
        """Test that get_rules loads ruleset and returns typed rules."""
        # Arrange
        test_rules = (
            ProcessingPurposeRule(
                name="test_purpose",
                description="Test processing purpose",
                patterns=("test_pattern",),
                risk_level="low",
                purpose_category="OPERATIONAL",
            ),
        )

        # Act
        with patch(
            "wct.analysers.utilities.ruleset_manager.RulesetLoader.load_ruleset"
        ) as mock_load:
            mock_load.return_value = test_rules
            result = RulesetManager.get_rules("test_ruleset", ProcessingPurposeRule)

        # Assert
        mock_load.assert_called_once_with("test_ruleset", ProcessingPurposeRule)
        assert result == test_rules
        assert len(result) == 1
        assert result[0].name == "test_purpose"

    def test_get_rules_propagates_ruleset_loader_exceptions(self) -> None:
        """Test that exceptions from RulesetLoader are propagated."""
        # Act & Assert
        with patch(
            "wct.analysers.utilities.ruleset_manager.RulesetLoader.load_ruleset"
        ) as mock_load:
            mock_load.side_effect = ValueError("Test error")

            with pytest.raises(ValueError, match="Test error"):
                RulesetManager.get_rules("invalid_ruleset", ProcessingPurposeRule)

    def test_get_rules_handles_empty_ruleset(self) -> None:
        """Test that get_rules handles empty rulesets correctly."""
        # Arrange - Empty tuple
        empty_rules: tuple[ProcessingPurposeRule, ...] = ()

        # Act
        with patch(
            "wct.analysers.utilities.ruleset_manager.RulesetLoader.load_ruleset"
        ) as mock_load:
            mock_load.return_value = empty_rules
            result = RulesetManager.get_rules("empty_ruleset", ProcessingPurposeRule)

        # Assert
        assert result == ()
        assert len(result) == 0

    def test_get_rules_works_with_different_rule_types(self) -> None:
        """Test that get_rules works with different rule types correctly."""
        # Arrange
        processing_rules = (
            ProcessingPurposeRule(
                name="purpose_rule",
                description="Test purpose",
                patterns=("purpose_pattern",),
                risk_level="medium",
                purpose_category="ANALYTICS",
            ),
        )

        # Act & Assert
        with patch(
            "wct.analysers.utilities.ruleset_manager.RulesetLoader.load_ruleset"
        ) as mock_load:
            mock_load.return_value = processing_rules

            result = RulesetManager.get_rules(
                "processing_purposes", ProcessingPurposeRule
            )

            mock_load.assert_called_with("processing_purposes", ProcessingPurposeRule)
            assert len(result) == 1
            assert result[0].purpose_category == "ANALYTICS"
