"""Unit tests for ruleset base classes and utilities."""

import pytest

from wct.rulesets.base import (
    Ruleset,
    RulesetAlreadyRegisteredError,
    RulesetLoader,
    RulesetNotFoundError,
    RulesetRegistry,
)
from wct.rulesets.types import ProcessingPurposeRule


class ConcreteRuleset(Ruleset[ProcessingPurposeRule]):
    """Concrete implementation of Ruleset for testing."""

    @property
    def name(self) -> str:
        """Return test name."""
        return "test_ruleset"

    @property
    def version(self) -> str:
        """Return test version."""
        return "1.0.0"

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

    def test_ruleset_get_rules_is_abstract(self):
        """Test that Ruleset.get_rules is an abstract method."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            Ruleset()  # type: ignore[abstract]

    def test_ruleset_initialisation_uses_name_property(self):
        """Test Ruleset initialisation uses name property."""
        ruleset = ConcreteRuleset()

        assert ruleset.name == "test_ruleset"

    def test_concrete_ruleset_get_rules_returns_list(self):
        """Test that concrete implementation returns list of rules."""
        ruleset = ConcreteRuleset()
        rules = ruleset.get_rules()

        assert isinstance(rules, tuple)
        assert len(rules) == 1
        assert isinstance(rules[0], ProcessingPurposeRule)
        assert rules[0].name == "test_rule"

    def test_concrete_ruleset_has_version(self):
        """Test that concrete implementation returns version."""
        ruleset = ConcreteRuleset()
        version = ruleset.version

        assert isinstance(version, str)
        assert version == "1.0.0"

    def test_ruleset_name_and_version_are_abstract(self):
        """Test that Ruleset.name and version are abstract properties."""

        class IncompleteRuleset(Ruleset):
            def get_rules(self) -> tuple[ProcessingPurposeRule, ...]:
                return ()

            # Missing name and version properties

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteRuleset()  # type: ignore[abstract]


class TestRulesetRegistry:
    """Test cases for the RulesetRegistry singleton."""

    def setup_method(self):
        """Reset the singleton instance before each test."""
        # Reset singleton instance to ensure clean state
        registry = RulesetRegistry()
        registry.clear()  # Use proper public API

    def teardown_method(self):
        """Clear registry after each test to prevent side effects."""
        registry = RulesetRegistry()
        registry.clear()  # Use proper public API

    def test_registry_is_singleton(self):
        """Test that RulesetRegistry implements singleton pattern."""
        registry1 = RulesetRegistry()
        registry2 = RulesetRegistry()

        assert registry1 is registry2

    def test_registry_initialises_empty_registry(self):
        """Test that registry starts with empty ruleset registry."""
        registry = RulesetRegistry()

        # Access private attribute for testing purposes
        assert registry._registry == {}  # type: ignore[attr-defined]

    def test_register_ruleset_class(self):
        """Test registering a ruleset class."""
        registry = RulesetRegistry()
        registry.register("test_ruleset", ConcreteRuleset, ProcessingPurposeRule)

        assert "test_ruleset" in registry._registry  # type: ignore[attr-defined]
        assert registry._registry["test_ruleset"] is ConcreteRuleset  # type: ignore[attr-defined]

    def test_get_registered_ruleset_class(self):
        """Test retrieving a registered ruleset class."""
        registry = RulesetRegistry()
        registry.register("test_ruleset", ConcreteRuleset, ProcessingPurposeRule)

        retrieved_class = registry.get_ruleset_class(
            "test_ruleset", ProcessingPurposeRule
        )

        assert retrieved_class is ConcreteRuleset

    def test_get_unregistered_ruleset_raises_error(self):
        """Test that getting an unregistered ruleset raises RulesetNotFoundError."""
        registry = RulesetRegistry()

        with pytest.raises(
            RulesetNotFoundError, match="Ruleset nonexistent not registered"
        ):
            registry.get_ruleset_class("nonexistent", ProcessingPurposeRule)

    def test_multiple_registrations_maintain_state(self):
        """Test that multiple registrations are maintained across singleton instances."""
        registry1 = RulesetRegistry()
        registry1.register("ruleset1", ConcreteRuleset, ProcessingPurposeRule)

        registry2 = RulesetRegistry()
        registry2.register("ruleset2", ConcreteRuleset, ProcessingPurposeRule)

        # Both should have access to all registrations
        assert (
            registry1.get_ruleset_class("ruleset1", ProcessingPurposeRule)
            is ConcreteRuleset
        )
        assert (
            registry1.get_ruleset_class("ruleset2", ProcessingPurposeRule)
            is ConcreteRuleset
        )
        assert (
            registry2.get_ruleset_class("ruleset1", ProcessingPurposeRule)
            is ConcreteRuleset
        )
        assert (
            registry2.get_ruleset_class("ruleset2", ProcessingPurposeRule)
            is ConcreteRuleset
        )

    def test_registry_prevents_duplicate_registration(self):
        """Test that registering the same name raises RulesetAlreadyRegisteredError."""

        class AnotherRuleset(Ruleset[ProcessingPurposeRule]):
            @property
            def name(self) -> str:
                return "another_test"

            @property
            def version(self) -> str:
                return "1.0.0"

            def get_rules(self) -> tuple[ProcessingPurposeRule, ...]:
                return ()

        registry = RulesetRegistry()
        registry.register("test_name", ConcreteRuleset, ProcessingPurposeRule)

        with pytest.raises(
            RulesetAlreadyRegisteredError,
            match="Ruleset 'test_name' is already registered",
        ):
            registry.register("test_name", AnotherRuleset, ProcessingPurposeRule)

        # Verify original registration is preserved
        retrieved_class = registry.get_ruleset_class("test_name", ProcessingPurposeRule)
        assert retrieved_class is ConcreteRuleset


class TestRulesetLoader:
    """Test cases for the RulesetLoader."""

    def setup_method(self):
        """Reset the singleton registry before each test."""
        registry = RulesetRegistry()
        registry.clear()  # Use proper public API

    def teardown_method(self):
        """Clear registry after each test to prevent side effects."""
        registry = RulesetRegistry()
        registry.clear()  # Use proper public API

    def test_load_ruleset_uses_registry(self):
        """Test that load_ruleset uses the singleton registry."""
        # Register a ruleset
        registry = RulesetRegistry()
        registry.register("test_ruleset", ConcreteRuleset, ProcessingPurposeRule)

        # Load the ruleset
        rules = RulesetLoader.load_ruleset("test_ruleset", ProcessingPurposeRule)

        assert isinstance(rules, tuple)
        assert len(rules) == 1
        assert rules[0].name == "test_rule"

    def test_load_nonexistent_ruleset_raises_error(self):
        """Test that loading a nonexistent ruleset raises RulesetNotFoundError."""
        with pytest.raises(
            RulesetNotFoundError, match="Ruleset nonexistent not registered"
        ):
            RulesetLoader.load_ruleset("nonexistent", ProcessingPurposeRule)

    def test_load_ruleset_creates_instance_with_correct_name(self):
        """Test that load_ruleset creates ruleset instance with correct name."""

        class NameTrackingRuleset(Ruleset[ProcessingPurposeRule]):
            @property
            def name(self) -> str:
                return "name_tracking"

            @property
            def version(self) -> str:
                return "1.0.0"

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

        registry = RulesetRegistry()
        registry.register("name_tracking", NameTrackingRuleset, ProcessingPurposeRule)

        rules = RulesetLoader.load_ruleset("name_tracking", ProcessingPurposeRule)

        assert len(rules) == 1
        assert rules[0].name == "rule_from_name_tracking"

    def test_load_ruleset_is_classmethod(self):
        """Test that load_ruleset can be called as a class method."""
        registry = RulesetRegistry()
        registry.register("class_method_test", ConcreteRuleset, ProcessingPurposeRule)

        # Should be callable without instantiating RulesetLoader
        rules = RulesetLoader.load_ruleset("class_method_test", ProcessingPurposeRule)

        assert isinstance(rules, tuple)
        assert len(rules) == 1


class TestRulesetIntegration:
    """Integration tests for ruleset components working together."""

    def setup_method(self):
        """Reset the singleton registry before each test."""
        registry = RulesetRegistry()
        registry.clear()  # Use proper public API

    def teardown_method(self):
        """Clear registry after each test to prevent side effects."""
        registry = RulesetRegistry()
        registry.clear()  # Use proper public API

    def test_end_to_end_ruleset_workflow(self):
        """Test the complete workflow from registration to loading."""

        # Define a custom ruleset
        class CustomRuleset(Ruleset[ProcessingPurposeRule]):
            @property
            def name(self) -> str:
                return "custom_rules"

            @property
            def version(self) -> str:
                return "1.0.0"

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

        # Register the ruleset
        registry = RulesetRegistry()
        registry.register("custom_rules", CustomRuleset, ProcessingPurposeRule)

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

    def test_ruleset_version_accessible_through_loader(self):
        """Test that ruleset version is accessible after loading."""

        class VersionedRuleset(Ruleset[ProcessingPurposeRule]):
            @property
            def name(self) -> str:
                return "versioned_rules"

            @property
            def version(self) -> str:
                return "3.2.1"

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

        registry = RulesetRegistry()
        registry.register("versioned_rules", VersionedRuleset, ProcessingPurposeRule)

        # Create an instance to check version
        ruleset_class = registry.get_ruleset_class(
            "versioned_rules", ProcessingPurposeRule
        )
        ruleset_instance = ruleset_class()

        assert ruleset_instance.version == "3.2.1"
