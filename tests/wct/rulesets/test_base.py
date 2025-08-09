"""Unit tests for ruleset base classes and utilities."""

import pytest

from wct.rulesets.base import (
    Ruleset,
    RulesetAlreadyRegisteredError,
    RulesetLoader,
    RulesetNotFoundError,
    RulesetRegistry,
)
from wct.rulesets.types import Rule


class ConcreteRuleset(Ruleset):
    """Concrete implementation of Ruleset for testing."""

    @property
    def version(self) -> str:
        """Return test version."""
        return "1.0.0"

    def get_rules(self) -> list[Rule]:
        """Return a test rule."""
        return [
            Rule(
                name="test_rule",
                description="Test rule for unit tests",
                patterns=("test_pattern", "test_pattern_2"),
                risk_level="low",
            )
        ]


class TestRulesetClass:
    """Test cases for the Ruleset abstract base class."""

    def test_ruleset_get_rules_is_abstract(self):
        """Test that Ruleset.get_rules is an abstract method."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            Ruleset("test")  # type: ignore[abstract]

    def test_ruleset_initialisation_with_name(self):
        """Test Ruleset initialisation with ruleset name."""
        ruleset = ConcreteRuleset("test_ruleset")

        assert ruleset.ruleset_name == "test_ruleset"

    def test_concrete_ruleset_get_rules_returns_list(self):
        """Test that concrete implementation returns list of rules."""
        ruleset = ConcreteRuleset("test_ruleset")
        rules = ruleset.get_rules()

        assert isinstance(rules, list)
        assert len(rules) == 1
        assert isinstance(rules[0], Rule)
        assert rules[0].name == "test_rule"

    def test_concrete_ruleset_has_version(self):
        """Test that concrete implementation returns version."""
        ruleset = ConcreteRuleset("test_ruleset")
        version = ruleset.version

        assert isinstance(version, str)
        assert version == "1.0.0"

    def test_ruleset_version_is_abstract(self):
        """Test that Ruleset.version is an abstract property."""

        class IncompleteRuleset(Ruleset):
            def get_rules(self) -> list[Rule]:
                return []

            # Missing version property

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteRuleset("test")  # type: ignore[abstract]


class TestRulesetRegistry:
    """Test cases for the RulesetRegistry singleton."""

    def setup_method(self):
        """Reset the singleton instance before each test."""
        # Reset singleton instance to ensure clean state
        RulesetRegistry._instance = None  # type: ignore[attr-defined]

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
        registry.register("test_ruleset", ConcreteRuleset)

        assert "test_ruleset" in registry._registry  # type: ignore[attr-defined]
        assert registry._registry["test_ruleset"] is ConcreteRuleset  # type: ignore[attr-defined]

    def test_get_registered_ruleset_class(self):
        """Test retrieving a registered ruleset class."""
        registry = RulesetRegistry()
        registry.register("test_ruleset", ConcreteRuleset)

        retrieved_class = registry.get_ruleset_class("test_ruleset")

        assert retrieved_class is ConcreteRuleset

    def test_get_unregistered_ruleset_raises_error(self):
        """Test that getting an unregistered ruleset raises RulesetNotFoundError."""
        registry = RulesetRegistry()

        with pytest.raises(
            RulesetNotFoundError, match="Ruleset nonexistent not registered"
        ):
            registry.get_ruleset_class("nonexistent")

    def test_multiple_registrations_maintain_state(self):
        """Test that multiple registrations are maintained across singleton instances."""
        registry1 = RulesetRegistry()
        registry1.register("ruleset1", ConcreteRuleset)

        registry2 = RulesetRegistry()
        registry2.register("ruleset2", ConcreteRuleset)

        # Both should have access to all registrations
        assert registry1.get_ruleset_class("ruleset1") is ConcreteRuleset
        assert registry1.get_ruleset_class("ruleset2") is ConcreteRuleset
        assert registry2.get_ruleset_class("ruleset1") is ConcreteRuleset
        assert registry2.get_ruleset_class("ruleset2") is ConcreteRuleset

    def test_registry_prevents_duplicate_registration(self):
        """Test that registering the same name raises RulesetAlreadyRegisteredError."""

        class AnotherRuleset(Ruleset):
            @property
            def version(self) -> str:
                return "1.0.0"

            def get_rules(self) -> list[Rule]:
                return []

        registry = RulesetRegistry()
        registry.register("test_name", ConcreteRuleset)

        with pytest.raises(
            RulesetAlreadyRegisteredError,
            match="Ruleset 'test_name' is already registered",
        ):
            registry.register("test_name", AnotherRuleset)

        # Verify original registration is preserved
        retrieved_class = registry.get_ruleset_class("test_name")
        assert retrieved_class is ConcreteRuleset


class TestRulesetLoader:
    """Test cases for the RulesetLoader."""

    def setup_method(self):
        """Reset the singleton registry before each test."""
        RulesetRegistry._instance = None  # type: ignore[attr-defined]

    def test_load_ruleset_uses_registry(self):
        """Test that load_ruleset uses the singleton registry."""
        # Register a ruleset
        registry = RulesetRegistry()
        registry.register("test_ruleset", ConcreteRuleset)

        # Load the ruleset
        rules = RulesetLoader.load_ruleset("test_ruleset")

        assert isinstance(rules, list)
        assert len(rules) == 1
        assert rules[0].name == "test_rule"

    def test_load_nonexistent_ruleset_raises_error(self):
        """Test that loading a nonexistent ruleset raises RulesetNotFoundError."""
        with pytest.raises(
            RulesetNotFoundError, match="Ruleset nonexistent not registered"
        ):
            RulesetLoader.load_ruleset("nonexistent")

    def test_load_ruleset_creates_instance_with_correct_name(self):
        """Test that load_ruleset creates ruleset instance with correct name."""

        class NameTrackingRuleset(Ruleset):
            @property
            def version(self) -> str:
                return "1.0.0"

            def get_rules(self) -> list[Rule]:
                # Return rule that includes the ruleset name for verification
                return [
                    Rule(
                        name=f"rule_from_{self.ruleset_name}",
                        description="Name tracking rule",
                        patterns=("test",),
                        risk_level="low",
                    )
                ]

        registry = RulesetRegistry()
        registry.register("name_tracking", NameTrackingRuleset)

        rules = RulesetLoader.load_ruleset("name_tracking")

        assert len(rules) == 1
        assert rules[0].name == "rule_from_name_tracking"

    def test_load_ruleset_is_classmethod(self):
        """Test that load_ruleset can be called as a class method."""
        registry = RulesetRegistry()
        registry.register("class_method_test", ConcreteRuleset)

        # Should be callable without instantiating RulesetLoader
        rules = RulesetLoader.load_ruleset("class_method_test")

        assert isinstance(rules, list)
        assert len(rules) == 1


class TestRulesetIntegration:
    """Integration tests for ruleset components working together."""

    def setup_method(self):
        """Reset the singleton registry before each test."""
        RulesetRegistry._instance = None  # type: ignore[attr-defined]

    def test_end_to_end_ruleset_workflow(self):
        """Test the complete workflow from registration to loading."""

        # Define a custom ruleset
        class CustomRuleset(Ruleset):
            @property
            def version(self) -> str:
                return "1.0.0"

            def get_rules(self) -> list[Rule]:
                return [
                    Rule(
                        name="custom_rule_1",
                        description="First custom rule",
                        patterns=("custom1", "pattern1"),
                        risk_level="medium",
                        metadata={"category": "test"},
                    ),
                    Rule(
                        name="custom_rule_2",
                        description="Second custom rule",
                        patterns=("custom2",),
                        risk_level="high",
                    ),
                ]

        # Register the ruleset
        registry = RulesetRegistry()
        registry.register("custom_rules", CustomRuleset)

        # Load the ruleset
        rules = RulesetLoader.load_ruleset("custom_rules")

        # Verify the complete workflow
        expected_rule_count = 2

        rule0 = rules[0]
        assert len(rules) == expected_rule_count
        assert rule0.name == "custom_rule_1"
        assert rule0.patterns == ("custom1", "pattern1")
        assert rule0.risk_level == "medium"
        assert rule0.metadata == {"category": "test"}

        rule1 = rules[1]
        assert rule1.name == "custom_rule_2"
        assert rule1.patterns == ("custom2",)
        assert rule1.risk_level == "high"
        assert rule1.metadata == {}

    def test_ruleset_version_accessible_through_loader(self):
        """Test that ruleset version is accessible after loading."""

        class VersionedRuleset(Ruleset):
            @property
            def version(self) -> str:
                return "3.2.1"

            def get_rules(self) -> list[Rule]:
                return [Rule("versioned", "Versioned rule", ("test",), "medium")]

        registry = RulesetRegistry()
        registry.register("versioned_rules", VersionedRuleset)

        # Create an instance to check version
        ruleset_class = registry.get_ruleset_class("versioned_rules")
        ruleset_instance = ruleset_class("versioned_rules")

        assert ruleset_instance.version == "3.2.1"
