"""Unit tests for ProcessingPurposesRuleset class."""

import pytest

from wct.rulesets.base import RulesetLoader, RulesetRegistry
from wct.rulesets.processing_purposes import ProcessingPurposesRuleset
from wct.rulesets.types import ProcessingPurposeRule, RuleComplianceData


class TestProcessingPurposesRuleset:
    """Test cases for the ProcessingPurposesRuleset class."""

    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.ruleset = ProcessingPurposesRuleset()

    def test_name_property_returns_canonical_name(self):
        """Test ProcessingPurposesRuleset returns canonical name."""
        ruleset = ProcessingPurposesRuleset()

        assert ruleset.name == "processing_purposes"

    def test_version_property_returns_correct_string_format(self):
        """Test that version property returns a non-empty string."""
        version = self.ruleset.version

        assert isinstance(version, str)
        assert len(version) > 0
        # Version should follow semantic versioning pattern (x.y.z)
        parts = version.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)

    def test_get_rules_returns_tuple_of_rules(self):
        """Test that get_rules returns an immutable tuple of Rule objects."""
        rules = self.ruleset.get_rules()

        assert isinstance(rules, tuple)
        assert len(rules) > 0
        assert all(isinstance(rule, ProcessingPurposeRule) for rule in rules)

    def test_get_rules_returns_consistent_count(self):
        """Test that get_rules returns a consistent number of rules."""
        rules1 = self.ruleset.get_rules()
        rules2 = self.ruleset.get_rules()

        assert len(rules1) == len(rules2)

    def test_rule_names_are_unique(self):
        """Test that all rule names are unique."""
        rules = self.ruleset.get_rules()
        rule_names = [rule.name for rule in rules]

        assert len(rule_names) == len(set(rule_names))

    def test_rules_have_correct_structure(self):
        """Test that each rule has the correct structure and required fields."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert hasattr(rule, "name")
            assert hasattr(rule, "description")
            assert hasattr(rule, "patterns")
            assert hasattr(rule, "risk_level")
            assert hasattr(rule, "purpose_category")

            assert isinstance(rule.name, str)
            assert isinstance(rule.description, str)
            assert isinstance(rule.patterns, tuple)
            assert isinstance(rule.risk_level, str)
            assert isinstance(rule.purpose_category, str)

    def test_rules_have_valid_risk_levels(self):
        """Test that all rules have valid risk levels."""
        rules = self.ruleset.get_rules()
        valid_risk_levels = {"low", "medium", "high"}

        for rule in rules:
            assert rule.risk_level in valid_risk_levels

    def test_rules_have_non_empty_patterns(self):
        """Test that all rules have non-empty pattern tuples."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert len(rule.patterns) > 0
            assert all(isinstance(pattern, str) for pattern in rule.patterns)
            assert all(len(pattern) > 0 for pattern in rule.patterns)

    def test_rules_have_non_empty_names_and_descriptions(self):
        """Test that all rules have non-empty names and descriptions."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert len(rule.name) > 0
            assert len(rule.description) > 0

    def test_rules_have_purpose_category_field(self):
        """Test that all rules have purpose_category field."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert isinstance(rule.purpose_category, str)
            assert len(rule.purpose_category) > 0

    def test_rules_have_compliance_information(self):
        """Test that all rules have compliance information."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert hasattr(rule, "compliance")
            assert isinstance(rule.compliance, list)
            assert len(rule.compliance) > 0

            # Check each compliance entry is a ComplianceData instance
            for compliance_item in rule.compliance:
                assert isinstance(compliance_item, RuleComplianceData)
                assert hasattr(compliance_item, "regulation")
                assert hasattr(compliance_item, "relevance")
                assert isinstance(compliance_item.regulation, str)
                assert isinstance(compliance_item.relevance, str)
                assert len(compliance_item.regulation) > 0
                assert len(compliance_item.relevance) > 0

    def test_get_rules_returns_same_tuple_each_time(self):
        """Test that get_rules returns the same immutable tuple instance each time."""
        rules1 = self.ruleset.get_rules()
        rules2 = self.ruleset.get_rules()

        assert rules1 is rules2  # Same tuple instance for immutability
        assert rules1 == rules2  # Same content

    def test_rules_are_immutable(self):
        """Test that returned rules tuple cannot be modified."""
        rules = self.ruleset.get_rules()

        # Verify tuple is immutable
        assert isinstance(rules, tuple)

        # Attempting to modify should raise TypeError
        with pytest.raises(AttributeError):
            rules.append(None)  # type: ignore[attr-defined]

        with pytest.raises(AttributeError):
            rules.clear()  # type: ignore[attr-defined]

        # Cannot assign to tuple elements
        with pytest.raises(TypeError):
            rules[0] = None  # type: ignore[index]


class TestProcessingPurposesIntegration:
    """Integration tests for ProcessingPurposesRuleset with other components."""

    def teardown_method(self):
        """Clear registry after each test to prevent side effects."""
        registry = RulesetRegistry()
        registry.clear()  # Use proper public API

    def test_ruleset_can_be_used_with_registry(self):
        """Test that ProcessingPurposesRuleset works with the registry pattern."""
        registry = RulesetRegistry()
        registry.clear()  # Use proper public API
        registry.register(
            "test_processing_purposes", ProcessingPurposesRuleset, ProcessingPurposeRule
        )

        # Should be able to retrieve and instantiate
        ruleset_class = registry.get_ruleset_class(
            "test_processing_purposes", ProcessingPurposeRule
        )
        assert ruleset_class is ProcessingPurposesRuleset

        instance = ruleset_class()
        assert isinstance(instance, ProcessingPurposesRuleset)
        assert instance.name == "processing_purposes"

    def test_ruleset_loader_integration(self):
        """Test that ProcessingPurposesRuleset works with RulesetLoader."""
        registry = RulesetRegistry()
        registry.clear()  # Use proper public API
        registry.register(
            "loader_test", ProcessingPurposesRuleset, ProcessingPurposeRule
        )

        # Load via RulesetLoader
        rules = RulesetLoader.load_ruleset("loader_test", ProcessingPurposeRule)

        assert isinstance(rules, tuple)
        assert len(rules) > 0
        assert all(isinstance(rule, ProcessingPurposeRule) for rule in rules)

        # Should have the same rules as direct instantiation
        direct_rules = ProcessingPurposesRuleset().get_rules()
        assert len(rules) == len(direct_rules)
