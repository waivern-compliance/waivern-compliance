"""Unit tests for RulesetRegistry."""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from waivern_rulesets.core.exceptions import RulesetNotFoundError
from waivern_rulesets.core.registry import RulesetRegistry
from waivern_rulesets.processing_purposes import ProcessingPurposeRule

from .conftest import (
    ConcreteRuleset,
    ConcreteRulesetV2,
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
