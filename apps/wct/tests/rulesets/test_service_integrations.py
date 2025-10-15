"""Tests for service integrations ruleset."""

import pytest

from wct.rulesets.base import RulesetLoader, RulesetRegistry
from wct.rulesets.service_integrations import (
    ServiceIntegrationRule,
    ServiceIntegrationsRuleset,
)


class TestServiceIntegrationRule:
    """Test cases for the ServiceIntegrationRule class."""

    def test_service_integration_rule_with_all_fields(self):
        """Test ServiceIntegrationRule with all fields."""
        rule = ServiceIntegrationRule(
            name="aws_integration",
            description="AWS integration rule",
            patterns=("aws", "s3.amazonaws"),
            service_category="cloud_infrastructure",
            purpose_category="OPERATIONAL",
            risk_level="medium",
        )

        assert rule.name == "aws_integration"
        assert rule.service_category == "cloud_infrastructure"
        assert rule.purpose_category == "OPERATIONAL"
        assert rule.risk_level == "medium"


class TestServiceIntegrationsRuleset:
    """Test suite for ServiceIntegrationsRuleset."""

    @pytest.fixture
    def ruleset(self) -> ServiceIntegrationsRuleset:
        """Create a ServiceIntegrationsRuleset instance for testing."""
        return ServiceIntegrationsRuleset()

    def test_name_property_returns_canonical_name(
        self, ruleset: ServiceIntegrationsRuleset
    ) -> None:
        """Test that name property returns the correct canonical name."""
        assert ruleset.name == "service_integrations"

    def test_version_property_returns_correct_string_format(
        self, ruleset: ServiceIntegrationsRuleset
    ) -> None:
        """Test that version property returns a valid version string."""
        version = ruleset.version
        assert isinstance(version, str)
        assert "." in version
        # Check it follows semantic versioning pattern (basic check)
        parts = version.split(".")
        assert len(parts) >= 2
        assert all(part.isdigit() for part in parts)

    def test_get_rules_returns_tuple_of_rules_with_at_least_one_rule(
        self, ruleset: ServiceIntegrationsRuleset
    ) -> None:
        """Test that get_rules returns a non-empty tuple of rules."""
        rules = ruleset.get_rules()
        assert isinstance(rules, tuple)
        assert len(rules) > 0

    def test_get_rules_returns_consistent_count(
        self, ruleset: ServiceIntegrationsRuleset
    ) -> None:
        """Test that get_rules returns the same count each time."""
        rules1 = ruleset.get_rules()
        rules2 = ruleset.get_rules()
        assert len(rules1) == len(rules2)

    def test_rule_names_are_unique(self, ruleset: ServiceIntegrationsRuleset) -> None:
        """Test that all rule names in the ruleset are unique."""
        rules = ruleset.get_rules()
        rule_names = [rule.name for rule in rules]
        assert len(rule_names) == len(set(rule_names))

    def test_rules_have_correct_structure(
        self, ruleset: ServiceIntegrationsRuleset
    ) -> None:
        """Test that all rules have the expected structure and required fields."""
        rules = ruleset.get_rules()
        for rule in rules:
            # Check required fields exist
            assert hasattr(rule, "name")
            assert hasattr(rule, "description")
            assert hasattr(rule, "patterns")
            assert hasattr(rule, "risk_level")
            assert hasattr(rule, "service_category")
            assert hasattr(rule, "purpose_category")

            # Check field types
            assert isinstance(rule.name, str)
            assert isinstance(rule.description, str)
            assert isinstance(rule.patterns, tuple)
            assert isinstance(rule.risk_level, str)
            assert isinstance(rule.service_category, str)
            assert isinstance(rule.purpose_category, str)

    def test_rules_have_valid_risk_levels(
        self, ruleset: ServiceIntegrationsRuleset
    ) -> None:
        """Test that all rules have valid risk levels."""
        rules = ruleset.get_rules()
        valid_risk_levels = {"low", "medium", "high"}
        for rule in rules:
            assert rule.risk_level in valid_risk_levels

    def test_rules_have_non_empty_patterns(
        self, ruleset: ServiceIntegrationsRuleset
    ) -> None:
        """Test that all rules have at least one pattern."""
        rules = ruleset.get_rules()
        for rule in rules:
            assert len(rule.patterns) > 0
            # Check that patterns are strings
            for pattern in rule.patterns:
                assert isinstance(pattern, str)
                assert len(pattern) > 0

    def test_rules_have_non_empty_names_and_descriptions(
        self, ruleset: ServiceIntegrationsRuleset
    ) -> None:
        """Test that all rules have non-empty names and descriptions."""
        rules = ruleset.get_rules()
        for rule in rules:
            assert len(rule.name) > 0
            assert len(rule.description) > 0

    def test_rules_have_service_category_field(
        self, ruleset: ServiceIntegrationsRuleset
    ) -> None:
        """Test that all rules have service_category field."""
        rules = ruleset.get_rules()
        for rule in rules:
            assert isinstance(rule.service_category, str)
            assert len(rule.service_category) > 0
            assert isinstance(rule.purpose_category, str)
            assert len(rule.purpose_category) > 0

    def test_patterns_are_tuples_not_lists(
        self, ruleset: ServiceIntegrationsRuleset
    ) -> None:
        """Test that patterns are stored as immutable tuples."""
        rules = ruleset.get_rules()
        for rule in rules:
            assert isinstance(rule.patterns, tuple)

    def test_get_rules_returns_same_tuple_each_time(
        self, ruleset: ServiceIntegrationsRuleset
    ) -> None:
        """Test that get_rules returns the same tuple object for performance."""
        rules1 = ruleset.get_rules()
        rules2 = ruleset.get_rules()
        assert rules1 is rules2  # Same object reference

    def test_rules_are_immutable(self, ruleset: ServiceIntegrationsRuleset) -> None:
        """Test that the rules tuple cannot be modified."""
        rules = ruleset.get_rules()
        original_length = len(rules)

        # Should not be able to modify the tuple
        with pytest.raises((TypeError, AttributeError)):
            rules.append("new_rule")  # type: ignore

        # Length should remain the same
        assert len(rules) == original_length


class TestServiceIntegrationsIntegration:
    """Integration tests for ServiceIntegrationsRuleset."""

    def test_ruleset_can_be_used_with_registry(self) -> None:
        """Test that the ruleset can be registered and retrieved."""
        registry = RulesetRegistry()
        registry.register(
            "test_service_integrations",
            ServiceIntegrationsRuleset,
            ServiceIntegrationRule,
        )

        retrieved_class = registry.get_ruleset_class(
            "test_service_integrations", ServiceIntegrationRule
        )
        assert retrieved_class == ServiceIntegrationsRuleset
        registry.clear()

    def test_ruleset_loader_integration(self) -> None:
        """Test that ServiceIntegrationsRuleset works with RulesetLoader."""
        # This should work since we register it in setup_method
        registry = RulesetRegistry()
        registry.register(
            "service_integrations", ServiceIntegrationsRuleset, ServiceIntegrationRule
        )
        rules = RulesetLoader.load_ruleset(
            "service_integrations", ServiceIntegrationRule
        )
        assert isinstance(rules, tuple)
        assert len(rules) > 0
        registry.clear()
