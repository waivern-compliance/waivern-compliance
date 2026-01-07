"""Tests for RulesetManager utility.

Note: Tests for RulesetURI parsing and provider validation are in
waivern-rulesets/tests/waivern_rulesets/test_base.py since those types
are defined in the waivern-rulesets package.

This file tests the RulesetManager caching layer only.
"""

from typing import Any
from unittest.mock import patch

import pytest
from waivern_rulesets.data_collection import DataCollectionRule
from waivern_rulesets.processing_purposes import ProcessingPurposeRule

from waivern_analysers_shared.utilities import RulesetManager

# =============================================================================
# RulesetManager Core Tests
# =============================================================================


class TestRulesetManager:
    """Test suite for RulesetManager utility class."""

    def setup_method(self) -> None:
        """Clear cache before each test to ensure clean state."""
        RulesetManager.clear_cache()

    def teardown_method(self) -> None:
        """Clear cache after each test to prevent side effects."""
        RulesetManager.clear_cache()

    def test_get_rules_loads_ruleset_successfully(self) -> None:
        """Test that get_rules loads ruleset and returns typed rules."""
        # Arrange
        test_rules = (
            ProcessingPurposeRule(
                name="test_purpose",
                description="Test processing purpose",
                patterns=("test_pattern",),
                purpose_category="OPERATIONAL",
            ),
        )

        # Act
        with patch(
            "waivern_analysers_shared.utilities.ruleset_manager.RulesetLoader.load_ruleset"
        ) as mock_load:
            mock_load.return_value = test_rules
            result = RulesetManager.get_rules(
                "local/test_ruleset/1.0.0", ProcessingPurposeRule
            )

        # Assert - RulesetLoader called with the full URI
        mock_load.assert_called_once_with(
            "local/test_ruleset/1.0.0", ProcessingPurposeRule
        )
        assert result == test_rules
        assert len(result) == 1
        assert result[0].name == "test_purpose"

    def test_get_rules_propagates_ruleset_loader_exceptions(self) -> None:
        """Test that exceptions from RulesetLoader are propagated."""
        # Act & Assert
        with patch(
            "waivern_analysers_shared.utilities.ruleset_manager.RulesetLoader.load_ruleset"
        ) as mock_load:
            mock_load.side_effect = ValueError("Test error")

            with pytest.raises(ValueError, match="Test error"):
                RulesetManager.get_rules(
                    "local/invalid_ruleset/1.0.0", ProcessingPurposeRule
                )

    def test_get_rules_handles_empty_ruleset(self) -> None:
        """Test that get_rules handles empty rulesets correctly."""
        # Arrange - Empty tuple
        empty_rules: tuple[ProcessingPurposeRule, ...] = ()

        # Act
        with patch(
            "waivern_analysers_shared.utilities.ruleset_manager.RulesetLoader.load_ruleset"
        ) as mock_load:
            mock_load.return_value = empty_rules
            result = RulesetManager.get_rules(
                "local/empty_ruleset/1.0.0", ProcessingPurposeRule
            )

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
                purpose_category="ANALYTICS",
            ),
        )

        # Act & Assert
        with patch(
            "waivern_analysers_shared.utilities.ruleset_manager.RulesetLoader.load_ruleset"
        ) as mock_load:
            mock_load.return_value = processing_rules

            result = RulesetManager.get_rules(
                "local/processing_purposes/1.0.0", ProcessingPurposeRule
            )

            mock_load.assert_called_with(
                "local/processing_purposes/1.0.0", ProcessingPurposeRule
            )
            assert len(result) == 1
            assert result[0].purpose_category == "ANALYTICS"


# =============================================================================
# RulesetManager Caching Tests
# =============================================================================


class TestRulesetManagerCaching:
    """Test suite for RulesetManager caching functionality."""

    def setup_method(self) -> None:
        """Clear cache before each test to ensure clean state."""
        RulesetManager.clear_cache()

    def teardown_method(self) -> None:
        """Clear cache after each test to prevent side effects."""
        RulesetManager.clear_cache()

    def test_caching_behavior_loads_ruleset_only_once(self) -> None:
        """Test that caching prevents multiple loads of the same ruleset."""
        # Arrange
        test_rules = (
            ProcessingPurposeRule(
                name="cached_rule",
                description="Test caching",
                patterns=("cache_test",),
                purpose_category="OPERATIONAL",
            ),
        )

        # Act - Make two identical calls
        with patch(
            "waivern_analysers_shared.utilities.ruleset_manager.RulesetLoader.load_ruleset"
        ) as mock_load:
            mock_load.return_value = test_rules

            result1 = RulesetManager.get_rules(
                "local/test_cache/1.0.0", ProcessingPurposeRule
            )
            result2 = RulesetManager.get_rules(
                "local/test_cache/1.0.0", ProcessingPurposeRule
            )

        # Assert - Loader called only once, but both results are identical
        mock_load.assert_called_once_with(
            "local/test_cache/1.0.0", ProcessingPurposeRule
        )
        assert result1 == result2
        assert result1 is result2  # Same cached object
        assert len(result1) == 1
        assert result1[0].name == "cached_rule"

    def test_cache_keys_distinguish_different_rule_types(self) -> None:
        """Test that different rule types create separate cache entries."""
        # Arrange
        processing_rules = (
            ProcessingPurposeRule(
                name="processing_rule",
                description="Processing rule",
                patterns=("processing",),
                purpose_category="ANALYTICS",
            ),
        )
        data_rules = (
            DataCollectionRule(
                name="data_rule",
                description="Data rule",
                patterns=("data",),
                collection_type="form_data",
                data_source="web_forms",
            ),
        )

        # Act - Load same ruleset name but different rule types
        with patch(
            "waivern_analysers_shared.utilities.ruleset_manager.RulesetLoader.load_ruleset"
        ) as mock_load:
            # Configure mock to return different rules based on rule type
            def side_effect(ruleset_name: str, rule_type: type[Any]) -> tuple[Any, ...]:
                if rule_type == ProcessingPurposeRule:
                    return processing_rules
                elif rule_type == DataCollectionRule:
                    return data_rules
                else:
                    raise ValueError(f"Unexpected rule type: {rule_type}")

            mock_load.side_effect = side_effect

            result1 = RulesetManager.get_rules(
                "local/multi_type/1.0.0", ProcessingPurposeRule
            )
            result2 = RulesetManager.get_rules(
                "local/multi_type/1.0.0", DataCollectionRule
            )

        # Assert - Both rule types loaded separately
        assert mock_load.call_count == 2
        mock_load.assert_any_call("local/multi_type/1.0.0", ProcessingPurposeRule)
        mock_load.assert_any_call("local/multi_type/1.0.0", DataCollectionRule)

        assert result1 != result2
        assert isinstance(result1[0], ProcessingPurposeRule)
        assert isinstance(result2[0], DataCollectionRule)
        assert result1[0].name == "processing_rule"
        assert result2[0].name == "data_rule"

    def test_clear_cache_forces_ruleset_reload(self) -> None:
        """Test that clear_cache forces subsequent calls to reload from RulesetLoader."""
        # Arrange
        test_rules = (
            ProcessingPurposeRule(
                name="clear_test",
                description="Cache clear test",
                patterns=("clear",),
                purpose_category="OPERATIONAL",
            ),
        )

        # Act - Load ruleset, clear cache, then load again
        with patch(
            "waivern_analysers_shared.utilities.ruleset_manager.RulesetLoader.load_ruleset"
        ) as mock_load:
            mock_load.return_value = test_rules

            # First load - should call RulesetLoader
            RulesetManager.get_rules("local/clear_test/1.0.0", ProcessingPurposeRule)
            assert mock_load.call_count == 1

            # Second load without clearing - should use cache (no additional calls)
            RulesetManager.get_rules("local/clear_test/1.0.0", ProcessingPurposeRule)
            assert mock_load.call_count == 1

            # Clear cache
            RulesetManager.clear_cache()

            # Third load after clearing - should call RulesetLoader again
            RulesetManager.get_rules("local/clear_test/1.0.0", ProcessingPurposeRule)
            assert mock_load.call_count == 2
