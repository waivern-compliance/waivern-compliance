"""Tests for RulesetManager utility.

Note: Tests for RulesetURI parsing and provider validation are in
waivern-rulesets/tests/waivern_rulesets/test_base.py since those types
are defined in the waivern-rulesets package.

This file tests the RulesetManager caching layer only.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from waivern_rulesets import AbstractRuleset
from waivern_rulesets.data_collection import DataCollectionRule
from waivern_rulesets.processing_purposes import ProcessingPurposeRule

from waivern_analysers_shared.utilities import RulesetManager


def _create_mock_ruleset(
    rules: tuple[Any, ...], name: str = "mock_ruleset", version: str = "1.0.0"
) -> MagicMock:
    """Create a mock ruleset instance with the given rules."""
    mock = MagicMock(spec=AbstractRuleset)
    mock.get_rules.return_value = rules
    mock.name = name
    mock.version = version
    return mock


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
        mock_ruleset = _create_mock_ruleset(test_rules)

        # Act
        with patch(
            "waivern_analysers_shared.utilities.ruleset_manager.RulesetLoader.load_ruleset_instance"
        ) as mock_load:
            mock_load.return_value = mock_ruleset
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

    def test_get_ruleset_returns_cached_instance(self) -> None:
        """Test that get_ruleset returns the full ruleset instance."""
        # Arrange
        test_rules = (
            ProcessingPurposeRule(
                name="test_purpose",
                description="Test processing purpose",
                patterns=("test_pattern",),
                purpose_category="OPERATIONAL",
            ),
        )
        mock_ruleset = _create_mock_ruleset(test_rules, name="test_ruleset")

        # Act
        with patch(
            "waivern_analysers_shared.utilities.ruleset_manager.RulesetLoader.load_ruleset_instance"
        ) as mock_load:
            mock_load.return_value = mock_ruleset
            ruleset = RulesetManager.get_ruleset(
                "local/test_ruleset/1.0.0", ProcessingPurposeRule
            )

        # Assert - Returns the full ruleset instance
        assert ruleset is mock_ruleset
        assert ruleset.name == "test_ruleset"
        assert ruleset.get_rules() == test_rules

    def test_get_rules_propagates_ruleset_loader_exceptions(self) -> None:
        """Test that exceptions from RulesetLoader are propagated."""
        # Act & Assert
        with patch(
            "waivern_analysers_shared.utilities.ruleset_manager.RulesetLoader.load_ruleset_instance"
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
        mock_ruleset = _create_mock_ruleset(empty_rules)

        # Act
        with patch(
            "waivern_analysers_shared.utilities.ruleset_manager.RulesetLoader.load_ruleset_instance"
        ) as mock_load:
            mock_load.return_value = mock_ruleset
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
        mock_ruleset = _create_mock_ruleset(processing_rules)

        # Act & Assert
        with patch(
            "waivern_analysers_shared.utilities.ruleset_manager.RulesetLoader.load_ruleset_instance"
        ) as mock_load:
            mock_load.return_value = mock_ruleset

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
        mock_ruleset = _create_mock_ruleset(test_rules)

        # Act - Make two identical calls
        with patch(
            "waivern_analysers_shared.utilities.ruleset_manager.RulesetLoader.load_ruleset_instance"
        ) as mock_load:
            mock_load.return_value = mock_ruleset

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
        assert result1 is result2  # Same cached object (rules from same ruleset)
        assert len(result1) == 1
        assert result1[0].name == "cached_rule"

    def test_get_ruleset_caching_returns_same_instance(self) -> None:
        """Test that get_ruleset returns the same cached instance on repeated calls."""
        # Arrange
        test_rules = (
            ProcessingPurposeRule(
                name="cached_rule",
                description="Test caching",
                patterns=("cache_test",),
                purpose_category="OPERATIONAL",
            ),
        )
        mock_ruleset = _create_mock_ruleset(test_rules)

        # Act - Make two identical calls to get_ruleset
        with patch(
            "waivern_analysers_shared.utilities.ruleset_manager.RulesetLoader.load_ruleset_instance"
        ) as mock_load:
            mock_load.return_value = mock_ruleset

            ruleset1 = RulesetManager.get_ruleset(
                "local/test_cache/1.0.0", ProcessingPurposeRule
            )
            ruleset2 = RulesetManager.get_ruleset(
                "local/test_cache/1.0.0", ProcessingPurposeRule
            )

        # Assert - Loader called only once, same instance returned
        mock_load.assert_called_once()
        assert ruleset1 is ruleset2  # Same cached instance

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
        mock_processing_ruleset = _create_mock_ruleset(processing_rules)
        mock_data_ruleset = _create_mock_ruleset(data_rules)

        # Act - Load same ruleset name but different rule types
        with patch(
            "waivern_analysers_shared.utilities.ruleset_manager.RulesetLoader.load_ruleset_instance"
        ) as mock_load:
            # Configure mock to return different rulesets based on rule type
            def side_effect(ruleset_uri: str, rule_type: type[Any]) -> MagicMock:
                if rule_type == ProcessingPurposeRule:
                    return mock_processing_ruleset
                elif rule_type == DataCollectionRule:
                    return mock_data_ruleset
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
        mock_ruleset = _create_mock_ruleset(test_rules)

        # Act - Load ruleset, clear cache, then load again
        with patch(
            "waivern_analysers_shared.utilities.ruleset_manager.RulesetLoader.load_ruleset_instance"
        ) as mock_load:
            mock_load.return_value = mock_ruleset

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
