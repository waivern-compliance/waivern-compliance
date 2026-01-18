"""Unit tests for RulesetRegistry."""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import MagicMock, patch

import pytest

from waivern_rulesets.core.exceptions import RulesetNotFoundError
from waivern_rulesets.core.registry import RulesetRegistry, extract_rule_type
from waivern_rulesets.personal_data_indicator import (
    PersonalDataIndicatorRule,
    PersonalDataIndicatorRuleset,
)
from waivern_rulesets.processing_purposes import ProcessingPurposeRule

from .conftest import (
    ConcreteRuleset,
    ConcreteRulesetV2,
    NonGenericClass,
    RulesetMissingName,
    RulesetMissingVersion,
)


class TestRulesetRegistry:
    """Test cases for the RulesetRegistry singleton."""

    def test_registry_is_singleton(self) -> None:
        """Test that RulesetRegistry implements singleton pattern."""
        registry1 = RulesetRegistry()
        registry2 = RulesetRegistry()

        assert registry1 is registry2

    def test_registry_can_be_cleared_to_empty(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that registry can be cleared to empty state."""
        # Clear registry for this specific test that needs empty state
        isolated_registry.clear()

        assert isolated_registry.is_empty()

    def test_register_extracts_name_version_from_class(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that register() auto-extracts name and version from ClassVars."""
        # New API: register(ruleset_class, rule_type) - no name argument
        isolated_registry.register(ConcreteRuleset, ProcessingPurposeRule)

        # Should be retrievable using ClassVar values (name + version)
        retrieved = isolated_registry.get_ruleset_class(
            "test_ruleset", "1.0.0", ProcessingPurposeRule
        )
        assert retrieved is ConcreteRuleset

    def test_register_makes_ruleset_retrievable(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test registering a ruleset makes it retrievable."""
        isolated_registry.register(ConcreteRuleset, ProcessingPurposeRule)

        retrieved = isolated_registry.get_ruleset_class(
            "test_ruleset", "1.0.0", ProcessingPurposeRule
        )

        assert retrieved is ConcreteRuleset

    def test_register_rejects_ruleset_missing_name(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that register() rejects rulesets without ruleset_name ClassVar."""
        with pytest.raises(ValueError, match="must define 'ruleset_name' ClassVar"):
            isolated_registry.register(RulesetMissingName, ProcessingPurposeRule)

    def test_register_rejects_ruleset_missing_version(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that register() rejects rulesets without ruleset_version ClassVar."""
        with pytest.raises(ValueError, match="must define 'ruleset_version' ClassVar"):
            isolated_registry.register(RulesetMissingVersion, ProcessingPurposeRule)

    def test_get_ruleset_class_requires_version(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that get_ruleset_class() requires version parameter."""
        isolated_registry.register(ConcreteRuleset, ProcessingPurposeRule)

        # Should work with correct version
        result = isolated_registry.get_ruleset_class(
            "test_ruleset", "1.0.0", ProcessingPurposeRule
        )
        assert result is ConcreteRuleset

        # Should fail with wrong version
        with pytest.raises(
            RulesetNotFoundError, match="version '9.9.9' not registered"
        ):
            isolated_registry.get_ruleset_class(
                "test_ruleset", "9.9.9", ProcessingPurposeRule
            )

    def test_get_unregistered_ruleset_raises_error(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that getting an unregistered ruleset raises RulesetNotFoundError."""
        isolated_registry.clear()

        with pytest.raises(RulesetNotFoundError, match="not registered"):
            isolated_registry.get_ruleset_class(
                "nonexistent", "1.0.0", ProcessingPurposeRule
            )

    def test_same_name_different_versions_both_registered(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that same ruleset name with different versions can coexist."""
        isolated_registry.register(ConcreteRuleset, ProcessingPurposeRule)
        isolated_registry.register(ConcreteRulesetV2, ProcessingPurposeRule)

        # Both versions should be retrievable
        v1 = isolated_registry.get_ruleset_class(
            "test_ruleset", "1.0.0", ProcessingPurposeRule
        )
        v2 = isolated_registry.get_ruleset_class(
            "test_ruleset", "2.0.0", ProcessingPurposeRule
        )

        assert v1 is ConcreteRuleset
        assert v2 is ConcreteRulesetV2
        assert v1 is not v2

    def test_registry_is_idempotent_for_duplicate_registration(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that registering same name+version is idempotent (no error)."""
        isolated_registry.register(ConcreteRuleset, ProcessingPurposeRule)

        # Second registration should silently succeed (idempotent)
        isolated_registry.register(ConcreteRuleset, ProcessingPurposeRule)

        # Should still be retrievable
        retrieved = isolated_registry.get_ruleset_class(
            "test_ruleset", "1.0.0", ProcessingPurposeRule
        )
        assert retrieved is ConcreteRuleset

    def test_is_registered_requires_version(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that is_registered() checks name+version combination."""
        isolated_registry.register(ConcreteRuleset, ProcessingPurposeRule)

        # Correct name+version
        assert isolated_registry.is_registered("test_ruleset", "1.0.0") is True

        # Wrong version
        assert isolated_registry.is_registered("test_ruleset", "9.9.9") is False

        # Wrong name
        assert isolated_registry.is_registered("nonexistent", "1.0.0") is False

    def test_get_available_versions_returns_all_versions(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that get_available_versions() lists all versions for a name."""
        isolated_registry.register(ConcreteRuleset, ProcessingPurposeRule)
        isolated_registry.register(ConcreteRulesetV2, ProcessingPurposeRule)

        versions = isolated_registry.get_available_versions("test_ruleset")

        assert set(versions) == {"1.0.0", "2.0.0"}

    def test_get_available_versions_returns_empty_for_unknown(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that get_available_versions() returns empty tuple for unknown name."""
        isolated_registry.clear()

        versions = isolated_registry.get_available_versions("nonexistent")

        assert versions == ()

    def test_registry_is_singleton_under_concurrent_access(self) -> None:
        """Test that RulesetRegistry maintains singleton under concurrent access.

        Verifies the double-checked locking pattern works correctly by spawning
        multiple threads that simultaneously attempt to get the registry instance.
        All threads should receive the exact same instance.
        """
        instances: list[RulesetRegistry] = []
        errors: list[Exception] = []
        num_threads = 50
        barrier = threading.Barrier(num_threads)

        def get_registry() -> None:
            try:
                # Wait for all threads to be ready before proceeding
                barrier.wait()
                instance = RulesetRegistry()
                instances.append(instance)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(get_registry) for _ in range(num_threads)]
            for future in as_completed(futures):
                future.result()  # Raise any exceptions

        assert not errors, f"Errors occurred: {errors}"
        assert len(instances) == num_threads

        # All instances should be the exact same object
        first_instance = instances[0]
        for instance in instances[1:]:
            assert instance is first_instance, "Different instances were created!"


class TestRulesetDiscovery:
    """Test cases for entry point based ruleset discovery."""

    def test_extract_rule_type_from_generic_parameter(self) -> None:
        """Test that extract_rule_type() extracts correct type from generic parameter."""
        result = extract_rule_type(PersonalDataIndicatorRuleset)

        assert result is PersonalDataIndicatorRule

    def test_extract_rule_type_raises_for_non_generic_class(self) -> None:
        """Test that extract_rule_type() raises error for non-generic class."""
        with pytest.raises(ValueError, match="Cannot extract rule type"):
            extract_rule_type(NonGenericClass)  # type: ignore[arg-type]

    def test_discover_from_entry_points_registers_rulesets(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that discover_from_entry_points() registers rulesets from entry points."""
        # Clear registry to start fresh
        isolated_registry.clear()

        # Create a mock entry point
        mock_ep = MagicMock()
        mock_ep.name = "personal_data_indicator"
        mock_ep.load.return_value = PersonalDataIndicatorRuleset

        with patch(
            "waivern_rulesets.core.registry.entry_points", return_value=[mock_ep]
        ):
            isolated_registry.discover_from_entry_points()

        # Verify ruleset was registered
        assert isolated_registry.is_registered("personal_data_indicator", "1.0.0")

        # Verify it can be retrieved with correct type
        result = isolated_registry.get_ruleset_class(
            "personal_data_indicator", "1.0.0", PersonalDataIndicatorRule
        )
        assert result is PersonalDataIndicatorRuleset

    def test_discover_from_entry_points_is_idempotent(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that calling discover_from_entry_points() twice is safe."""
        isolated_registry.clear()

        mock_ep = MagicMock()
        mock_ep.name = "personal_data_indicator"
        mock_ep.load.return_value = PersonalDataIndicatorRuleset

        with patch(
            "waivern_rulesets.core.registry.entry_points", return_value=[mock_ep]
        ):
            # First call
            isolated_registry.discover_from_entry_points()
            # Second call should not raise
            isolated_registry.discover_from_entry_points()

        # Should still be registered correctly
        assert isolated_registry.is_registered("personal_data_indicator", "1.0.0")

    def test_discover_from_entry_points_logs_warning_for_invalid_entry(
        self, isolated_registry: RulesetRegistry, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that invalid entry points log warning but don't break discovery."""
        isolated_registry.clear()

        # Create one valid and one invalid entry point
        valid_ep = MagicMock()
        valid_ep.name = "personal_data_indicator"
        valid_ep.load.return_value = PersonalDataIndicatorRuleset

        invalid_ep = MagicMock()
        invalid_ep.name = "broken_ruleset"
        invalid_ep.load.side_effect = ImportError("Module not found")

        with patch(
            "waivern_rulesets.core.registry.entry_points",
            return_value=[invalid_ep, valid_ep],
        ):
            with caplog.at_level(logging.WARNING):
                isolated_registry.discover_from_entry_points()

        # Invalid entry should log warning
        assert "Failed to load ruleset from entry point 'broken_ruleset'" in caplog.text

        # Valid entry should still be registered
        assert isolated_registry.is_registered("personal_data_indicator", "1.0.0")
