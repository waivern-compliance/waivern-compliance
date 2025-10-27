"""Unit tests for ruleset base classes and utilities."""

from typing import override

import pytest

from waivern_rulesets.base import (
    AbstractRuleset,
    RulesetAlreadyRegisteredError,
    RulesetLoader,
    RulesetNotFoundError,
    RulesetRegistry,
)
from waivern_rulesets.processing_purposes import ProcessingPurposeRule


class ConcreteRuleset(AbstractRuleset[ProcessingPurposeRule]):
    """Concrete implementation of Ruleset for testing."""

    @property
    @override
    def name(self) -> str:
        """Return test name."""
        return "test_ruleset"

    @property
    @override
    def version(self) -> str:
        """Return test version."""
        return "1.0.0"

    @override
    def get_rules(self) -> tuple[ProcessingPurposeRule, ...]:
        """Return a test rule."""
        return (
            ProcessingPurposeRule(
                name="test_rule",
                description="Test rule for unit tests",
                patterns=("test_pattern", "test_pattern_2"),
                risk_level="low",
                purpose_category="OPERATIONAL",
            ),
        )


class TestRulesetClass:
    """Test cases for the Ruleset abstract base class."""

    def test_ruleset_get_rules_is_abstract(self) -> None:
        """Test that Ruleset.get_rules is an abstract method."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            AbstractRuleset()  # type: ignore[abstract]

    def test_ruleset_initialisation_uses_name_property(self) -> None:
        """Test Ruleset initialisation uses name property."""
        ruleset = ConcreteRuleset()

        assert ruleset.name == "test_ruleset"

    def test_concrete_ruleset_get_rules_returns_list(self) -> None:
        """Test that concrete implementation returns list of rules."""
        ruleset = ConcreteRuleset()
        rules = ruleset.get_rules()

        assert isinstance(rules, tuple)
        assert len(rules) == 1
        assert isinstance(rules[0], ProcessingPurposeRule)
        assert rules[0].name == "test_rule"

    def test_concrete_ruleset_has_version(self) -> None:
        """Test that concrete implementation returns version."""
        ruleset = ConcreteRuleset()
        version = ruleset.version

        assert isinstance(version, str)
        assert version == "1.0.0"

    def test_ruleset_name_and_version_are_abstract(self) -> None:
        """Test that Ruleset.name and version are abstract properties."""

        class IncompleteRuleset(AbstractRuleset[ProcessingPurposeRule]):
            @override
            def get_rules(self) -> tuple[ProcessingPurposeRule, ...]:
                return ()

            # Missing name and version properties

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteRuleset()  # type: ignore[abstract]


class TestRulesetRegistry:
    """Test cases for the RulesetRegistry singleton."""

    def test_registry_is_singleton(self) -> None:
        """Test that RulesetRegistry implements singleton pattern."""
        registry1 = RulesetRegistry()
        registry2 = RulesetRegistry()

        assert registry1 is registry2

    def test_registry_initialises_empty_registry(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that registry starts with empty ruleset registry."""
        isolated_registry.clear()

        # Access private attribute for testing purposes
        assert isolated_registry._registry == {}  # type: ignore[attr-defined]

    def test_register_ruleset_class(self, isolated_registry: RulesetRegistry) -> None:
        """Test registering a ruleset class."""
        isolated_registry.clear()
        isolated_registry.register(
            "test_ruleset", ConcreteRuleset, ProcessingPurposeRule
        )

        assert "test_ruleset" in isolated_registry._registry  # type: ignore[attr-defined]
        assert isolated_registry._registry["test_ruleset"] is ConcreteRuleset  # type: ignore[attr-defined]

    def test_get_registered_ruleset_class(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test retrieving a registered ruleset class."""
        isolated_registry.clear()
        isolated_registry.register(
            "test_ruleset", ConcreteRuleset, ProcessingPurposeRule
        )

        retrieved_class = isolated_registry.get_ruleset_class(
            "test_ruleset", ProcessingPurposeRule
        )

        assert retrieved_class is ConcreteRuleset

    def test_get_unregistered_ruleset_raises_error(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that getting an unregistered ruleset raises RulesetNotFoundError."""
        isolated_registry.clear()

        with pytest.raises(
            RulesetNotFoundError, match="Ruleset nonexistent not registered"
        ):
            isolated_registry.get_ruleset_class("nonexistent", ProcessingPurposeRule)

    def test_multiple_registrations_maintain_state(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that multiple registrations are maintained across singleton instances."""
        isolated_registry.clear()
        isolated_registry.register("ruleset1", ConcreteRuleset, ProcessingPurposeRule)
        isolated_registry.register("ruleset2", ConcreteRuleset, ProcessingPurposeRule)

        # Both should have access to all registrations
        assert (
            isolated_registry.get_ruleset_class("ruleset1", ProcessingPurposeRule)
            is ConcreteRuleset
        )
        assert (
            isolated_registry.get_ruleset_class("ruleset2", ProcessingPurposeRule)
            is ConcreteRuleset
        )

    def test_registry_prevents_duplicate_registration(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that registering the same name raises RulesetAlreadyRegisteredError."""

        class AnotherRuleset(AbstractRuleset[ProcessingPurposeRule]):
            @property
            @override
            def name(self) -> str:
                return "another_test"

            @property
            @override
            def version(self) -> str:
                return "1.0.0"

            @override
            def get_rules(self) -> tuple[ProcessingPurposeRule, ...]:
                return ()

        isolated_registry.clear()
        isolated_registry.register("test_name", ConcreteRuleset, ProcessingPurposeRule)

        with pytest.raises(
            RulesetAlreadyRegisteredError,
            match="Ruleset 'test_name' is already registered",
        ):
            isolated_registry.register(
                "test_name", AnotherRuleset, ProcessingPurposeRule
            )

        # Verify original registration is preserved
        retrieved_class = isolated_registry.get_ruleset_class(
            "test_name", ProcessingPurposeRule
        )
        assert retrieved_class is ConcreteRuleset


class TestRulesetLoader:
    """Test cases for the RulesetLoader."""

    def test_load_ruleset_uses_registry(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that load_ruleset uses the singleton registry."""
        isolated_registry.clear()
        isolated_registry.register(
            "test_ruleset", ConcreteRuleset, ProcessingPurposeRule
        )

        # Load the ruleset
        rules = RulesetLoader.load_ruleset("test_ruleset", ProcessingPurposeRule)

        assert isinstance(rules, tuple)
        assert len(rules) == 1
        assert rules[0].name == "test_rule"

    def test_load_nonexistent_ruleset_raises_error(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that loading a nonexistent ruleset raises RulesetNotFoundError."""
        isolated_registry.clear()

        with pytest.raises(
            RulesetNotFoundError, match="Ruleset nonexistent not registered"
        ):
            RulesetLoader.load_ruleset("nonexistent", ProcessingPurposeRule)

    def test_load_ruleset_creates_instance_with_correct_name(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that load_ruleset creates ruleset instance with correct name."""

        class NameTrackingRuleset(AbstractRuleset[ProcessingPurposeRule]):
            @property
            @override
            def name(self) -> str:
                return "name_tracking"

            @property
            @override
            def version(self) -> str:
                return "1.0.0"

            @override
            def get_rules(self) -> tuple[ProcessingPurposeRule, ...]:
                # Return rule that includes the ruleset name for verification
                return (
                    ProcessingPurposeRule(
                        name=f"rule_from_{self.name}",
                        description="Name tracking rule",
                        patterns=("test",),
                        risk_level="low",
                        purpose_category="OPERATIONAL",
                    ),
                )

        isolated_registry.clear()
        isolated_registry.register(
            "name_tracking", NameTrackingRuleset, ProcessingPurposeRule
        )

        rules = RulesetLoader.load_ruleset("name_tracking", ProcessingPurposeRule)

        assert len(rules) == 1
        assert rules[0].name == "rule_from_name_tracking"

    def test_load_ruleset_is_classmethod(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that load_ruleset can be called as a class method."""
        isolated_registry.clear()
        isolated_registry.register(
            "class_method_test", ConcreteRuleset, ProcessingPurposeRule
        )

        # Should be callable without instantiating RulesetLoader
        rules = RulesetLoader.load_ruleset("class_method_test", ProcessingPurposeRule)

        assert isinstance(rules, tuple)
        assert len(rules) == 1


class TestRulesetIntegration:
    """Integration tests for ruleset components working together."""

    def test_end_to_end_ruleset_workflow(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test the complete workflow from registration to loading."""

        # Define a custom ruleset
        class CustomRuleset(AbstractRuleset[ProcessingPurposeRule]):
            @property
            @override
            def name(self) -> str:
                return "custom_rules"

            @property
            @override
            def version(self) -> str:
                return "1.0.0"

            @override
            def get_rules(self) -> tuple[ProcessingPurposeRule, ...]:
                return (
                    ProcessingPurposeRule(
                        name="custom_rule_1",
                        description="First custom rule",
                        patterns=("custom1", "pattern1"),
                        risk_level="medium",
                        purpose_category="ANALYTICS",
                    ),
                    ProcessingPurposeRule(
                        name="custom_rule_2",
                        description="Second custom rule",
                        patterns=("custom2",),
                        risk_level="high",
                        purpose_category="OPERATIONAL",
                    ),
                )

        isolated_registry.clear()
        isolated_registry.register("custom_rules", CustomRuleset, ProcessingPurposeRule)

        # Load the ruleset
        rules = RulesetLoader.load_ruleset("custom_rules", ProcessingPurposeRule)

        # Verify the complete workflow
        expected_rule_count = 2

        rule0 = rules[0]
        assert len(rules) == expected_rule_count
        assert rule0.name == "custom_rule_1"
        assert rule0.patterns == ("custom1", "pattern1")
        assert rule0.risk_level == "medium"
        assert rule0.purpose_category == "ANALYTICS"

        rule1 = rules[1]
        assert rule1.name == "custom_rule_2"
        assert rule1.patterns == ("custom2",)
        assert rule1.risk_level == "high"
        assert rule1.purpose_category == "OPERATIONAL"

    def test_ruleset_version_accessible_through_loader(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that ruleset version is accessible after loading."""

        class VersionedRuleset(AbstractRuleset[ProcessingPurposeRule]):
            @property
            @override
            def name(self) -> str:
                return "versioned_rules"

            @property
            @override
            def version(self) -> str:
                return "3.2.1"

            @override
            def get_rules(self) -> tuple[ProcessingPurposeRule, ...]:
                return (
                    ProcessingPurposeRule(
                        name="versioned",
                        description="Versioned rule",
                        patterns=("test",),
                        risk_level="medium",
                        purpose_category="OPERATIONAL",
                    ),
                )

        isolated_registry.clear()
        isolated_registry.register(
            "versioned_rules", VersionedRuleset, ProcessingPurposeRule
        )

        # Create an instance to check version
        ruleset_class = isolated_registry.get_ruleset_class(
            "versioned_rules", ProcessingPurposeRule
        )
        ruleset_instance = ruleset_class()

        assert ruleset_instance.version == "3.2.1"
