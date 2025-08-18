"""Tests for RulesetManager utility."""

from unittest.mock import patch

import pytest

from wct.analysers.utilities import RulesetManager
from wct.rulesets.types import Rule


class TestRulesetManagerSingleton:
    """Test suite for RulesetManager singleton behaviour."""

    def teardown_method(self) -> None:
        """Clear cache after each test using public API."""
        manager = RulesetManager()
        manager.clear_cache()

    def test_returns_same_instance_when_created_multiple_times(self) -> None:
        """Test that RulesetManager returns the same instance (singleton pattern)."""
        # Act
        instance1 = RulesetManager()
        instance2 = RulesetManager()

        # Assert
        assert instance1 is instance2

    def test_multiple_instantiations_share_same_cache(self) -> None:
        """Test that multiple instances share the same cache."""
        # Arrange
        test_rules = (
            Rule(
                name="test_rule",
                description="Test rule",
                patterns=("test_pattern",),
                risk_level="low",
                metadata={},
            ),
        )

        # Act
        manager1 = RulesetManager()
        manager2 = RulesetManager()

        # Mock the RulesetLoader to return test rules
        with patch(
            "wct.analysers.utilities.ruleset_manager.RulesetLoader.load_ruleset"
        ) as mock_load:
            mock_load.return_value = test_rules

            # Load ruleset with first instance
            manager1.get_rules("test_ruleset")

            # Access with second instance should use cache
            result = manager2.get_rules("test_ruleset")

        # Assert
        assert result == test_rules
        # Should only call load_ruleset once due to caching
        mock_load.assert_called_once_with("test_ruleset")


class TestRulesetManagerGetRules:
    """Test suite for RulesetManager get_rules functionality."""

    def teardown_method(self) -> None:
        """Clear cache after each test using public API."""
        manager = RulesetManager()
        manager.clear_cache()

    def test_loads_ruleset_successfully(self) -> None:
        """Test that get_rules loads a ruleset successfully."""
        # Arrange
        test_rules = (
            Rule(
                name="email",
                description="Email address pattern",
                patterns=("@", "email"),
                risk_level="medium",
                metadata={"special_category": "N"},
            ),
            Rule(
                name="phone",
                description="Phone number pattern",
                patterns=("phone", "tel:"),
                risk_level="high",
                metadata={"special_category": "N"},
            ),
        )

        manager = RulesetManager()

        # Act
        with patch(
            "wct.analysers.utilities.ruleset_manager.RulesetLoader.load_ruleset"
        ) as mock_load:
            mock_load.return_value = test_rules
            result = manager.get_rules("personal_data")

        # Assert
        assert result == test_rules
        assert len(result) == 2
        assert result[0].name == "email"
        assert result[1].name == "phone"
        mock_load.assert_called_once_with("personal_data")

    def test_caches_ruleset_after_first_load(self) -> None:
        """Test that rulesets are cached and subsequent calls don't reload."""
        # Arrange
        test_rules = (
            Rule(
                name="cached_rule",
                description="Cached rule",
                patterns=("cache_test",),
                risk_level="low",
                metadata={},
            ),
        )

        manager = RulesetManager()

        # Act
        with patch(
            "wct.analysers.utilities.ruleset_manager.RulesetLoader.load_ruleset"
        ) as mock_load:
            mock_load.return_value = test_rules

            # First call should load from RulesetLoader
            result1 = manager.get_rules("cached_ruleset")

            # Second call should use cache
            result2 = manager.get_rules("cached_ruleset")

        # Assert
        assert result1 == test_rules
        assert result2 == test_rules
        assert result1 is result2  # Should be the same cached object
        # Should only call load_ruleset once
        mock_load.assert_called_once_with("cached_ruleset")

    def test_loads_different_rulesets_independently(self) -> None:
        """Test that different rulesets are loaded and cached independently."""
        # Arrange
        personal_data_rules = (
            Rule(
                name="email",
                description="Email",
                patterns=("@",),
                risk_level="medium",
                metadata={},
            ),
        )
        processing_purpose_rules = (
            Rule(
                name="marketing",
                description="Marketing",
                patterns=("advertisement",),
                risk_level="low",
                metadata={},
            ),
        )

        manager = RulesetManager()

        # Act
        with patch(
            "wct.analysers.utilities.ruleset_manager.RulesetLoader.load_ruleset"
        ) as mock_load:
            mock_load.side_effect = [personal_data_rules, processing_purpose_rules]

            result1 = manager.get_rules("personal_data")
            result2 = manager.get_rules("processing_purpose")

        # Assert
        assert result1 == personal_data_rules
        assert result2 == processing_purpose_rules
        assert result1 != result2
        assert mock_load.call_count == 2

    def test_handles_empty_ruleset(self) -> None:
        """Test that empty rulesets are handled correctly."""
        # Arrange
        empty_rules = ()
        manager = RulesetManager()

        # Act
        with patch(
            "wct.analysers.utilities.ruleset_manager.RulesetLoader.load_ruleset"
        ) as mock_load:
            mock_load.return_value = empty_rules
            result = manager.get_rules("empty_ruleset")

        # Assert
        assert result == ()
        assert len(result) == 0
        mock_load.assert_called_once_with("empty_ruleset")

    def test_propagates_ruleset_loader_exceptions(self) -> None:
        """Test that exceptions from RulesetLoader are propagated correctly."""
        # Arrange
        manager = RulesetManager()
        expected_error = FileNotFoundError("Ruleset file not found")

        # Act & Assert
        with patch(
            "wct.analysers.utilities.ruleset_manager.RulesetLoader.load_ruleset"
        ) as mock_load:
            mock_load.side_effect = expected_error

            with pytest.raises(FileNotFoundError, match="Ruleset file not found"):
                manager.get_rules("nonexistent_ruleset")

    def test_handles_empty_string_ruleset_name(self) -> None:
        """Test behaviour with empty string ruleset name."""
        # Arrange
        manager = RulesetManager()

        # Act & Assert
        with patch(
            "wct.analysers.utilities.ruleset_manager.RulesetLoader.load_ruleset"
        ) as mock_load:
            mock_load.side_effect = ValueError("Invalid ruleset name")

            with pytest.raises(ValueError, match="Invalid ruleset name"):
                manager.get_rules("")


class TestRulesetManagerClearCache:
    """Test suite for RulesetManager cache clearing functionality."""

    def teardown_method(self) -> None:
        """Clear cache after each test using public API."""
        manager = RulesetManager()
        manager.clear_cache()

    def test_clears_cache_successfully(self) -> None:
        """Test that clear_cache removes cached rulesets."""
        # Arrange
        test_rules = (
            Rule(
                name="test",
                description="Test",
                patterns=("test",),
                risk_level="low",
                metadata={},
            ),
        )

        manager = RulesetManager()

        # Load a ruleset to populate cache
        with patch(
            "wct.analysers.utilities.ruleset_manager.RulesetLoader.load_ruleset"
        ) as mock_load:
            mock_load.return_value = test_rules
            manager.get_rules("test_ruleset")

            # Clear cache
            manager.clear_cache()

            # Access again should reload from RulesetLoader
            manager.get_rules("test_ruleset")

        # Assert
        # Should call load_ruleset twice: once before clear, once after clear
        assert mock_load.call_count == 2

    def test_clear_cache_on_empty_cache_succeeds(self) -> None:
        """Test that clearing an empty cache succeeds without error."""
        # Arrange
        manager = RulesetManager()

        # Act & Assert - should not raise any exceptions
        manager.clear_cache()

    def test_clear_cache_affects_all_instances(self) -> None:
        """Test that clearing cache affects all instances due to singleton pattern."""
        # Arrange
        test_rules = (
            Rule(
                name="shared",
                description="Shared",
                patterns=("shared",),
                risk_level="medium",
                metadata={},
            ),
        )

        manager1 = RulesetManager()
        manager2 = RulesetManager()

        # Act
        with patch(
            "wct.analysers.utilities.ruleset_manager.RulesetLoader.load_ruleset"
        ) as mock_load:
            mock_load.return_value = test_rules

            # Load with first instance
            manager1.get_rules("shared_ruleset")

            # Clear with second instance
            manager2.clear_cache()

            # Access with first instance should reload
            manager1.get_rules("shared_ruleset")

        # Assert
        # Should call load_ruleset twice: once before clear, once after clear
        assert mock_load.call_count == 2


class TestRulesetManagerIntegration:
    """Integration tests for RulesetManager."""

    def teardown_method(self) -> None:
        """Clear cache after each test using public API."""
        manager = RulesetManager()
        manager.clear_cache()

    def test_realistic_usage_scenario(self) -> None:
        """Test a realistic usage scenario with multiple rulesets and cache operations."""
        # Arrange
        personal_data_rules = (
            Rule(
                name="email",
                description="Email",
                patterns=("@", ".com"),
                risk_level="medium",
                metadata={},
            ),
            Rule(
                name="ssn",
                description="SSN",
                patterns=("###-##-####",),
                risk_level="high",
                metadata={},
            ),
        )

        processing_rules = (
            Rule(
                name="marketing",
                description="Marketing",
                patterns=("promotion",),
                risk_level="low",
                metadata={},
            ),
        )

        manager = RulesetManager()

        # Act
        with patch(
            "wct.analysers.utilities.ruleset_manager.RulesetLoader.load_ruleset"
        ) as mock_load:
            mock_load.side_effect = [
                personal_data_rules,
                processing_rules,
                personal_data_rules,
            ]

            # Load personal data rules
            pd_result1 = manager.get_rules("personal_data")

            # Load processing purpose rules
            pp_result = manager.get_rules("processing_purpose")

            # Access personal data rules again (should use cache)
            pd_result2 = manager.get_rules("personal_data")

            # Clear cache and reload
            manager.clear_cache()
            pd_result3 = manager.get_rules("personal_data")

        # Assert
        assert pd_result1 == personal_data_rules
        assert pp_result == processing_rules
        assert pd_result2 == personal_data_rules
        assert pd_result3 == personal_data_rules

        # Should call load_ruleset 3 times:
        # 1. personal_data (first load)
        # 2. processing_purpose
        # 3. personal_data (after cache clear)
        assert mock_load.call_count == 3

    def test_concurrent_access_pattern(self) -> None:
        """Test pattern that simulates concurrent access to the same ruleset."""
        # Arrange
        test_rules = (
            Rule(
                name="concurrent",
                description="Concurrent test",
                patterns=("test",),
                risk_level="low",
                metadata={},
            ),
        )

        # Simulate multiple "clients" accessing the same manager
        manager_client1 = RulesetManager()
        manager_client2 = RulesetManager()
        manager_client3 = RulesetManager()

        # Act
        with patch(
            "wct.analysers.utilities.ruleset_manager.RulesetLoader.load_ruleset"
        ) as mock_load:
            mock_load.return_value = test_rules

            # Multiple clients access the same ruleset
            result1 = manager_client1.get_rules("concurrent_ruleset")
            result2 = manager_client2.get_rules("concurrent_ruleset")
            result3 = manager_client3.get_rules("concurrent_ruleset")

        # Assert
        assert result1 == test_rules
        assert result2 == test_rules
        assert result3 == test_rules
        assert result1 is result2 is result3  # Same cached object
        # Should only load once due to caching
        mock_load.assert_called_once_with("concurrent_ruleset")
