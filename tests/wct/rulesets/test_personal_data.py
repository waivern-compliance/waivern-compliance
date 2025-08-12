"""Unit tests for PersonalDataRuleset class."""

import pytest

from wct.rulesets.base import RulesetLoader, RulesetRegistry
from wct.rulesets.personal_data import PersonalDataRuleset
from wct.rulesets.types import Rule


class TestPersonalDataRuleset:
    """Test cases for the PersonalDataRuleset class."""

    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.ruleset = PersonalDataRuleset()

    def test_name_property_returns_canonical_name(self):
        """Test PersonalDataRuleset returns canonical name."""
        ruleset = PersonalDataRuleset()

        assert ruleset.name == "personal_data"

    def test_version_property_returns_correct_string_format(self):
        """Test that version property returns a non-empty string."""
        version = self.ruleset.version

        assert isinstance(version, str)
        assert len(version) > 0
        # Version should follow semantic versioning pattern (x.y.z)
        parts = version.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)

    def test_get_rules_returns_tuple_of_rules_with_at_least_one_rule(self):
        """Test that get_rules returns an immutable tuple of Rule objects."""
        rules = self.ruleset.get_rules()

        assert isinstance(rules, tuple)
        assert len(rules) > 0
        assert all(isinstance(rule, Rule) for rule in rules)

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
            assert hasattr(rule, "metadata")

            assert isinstance(rule.name, str)
            assert isinstance(rule.description, str)
            assert isinstance(rule.patterns, tuple)
            assert isinstance(rule.risk_level, str)
            assert isinstance(rule.metadata, dict)

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

    def test_rules_have_special_category_when_gdpr_relevant(self):
        """Test that rules have special_category metadata when GDPR is relevant."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            # If GDPR is listed in compliance relevance, special_category is required
            if (
                "compliance_relevance" in rule.metadata
                and "GDPR" in rule.metadata["compliance_relevance"]
            ):
                assert "special_category" in rule.metadata
                assert isinstance(rule.metadata["special_category"], str)
                assert rule.metadata["special_category"] in {"Y", "N"}

    def test_gdpr_article_9_special_categories_exist(self):
        """Test that GDPR Article 9 special category rules exist."""
        rules = self.ruleset.get_rules()
        rule_names = [rule.name.lower() for rule in rules]

        # Should have health, genetic, biometric data rules
        health_terms_found = [name for name in rule_names if "health" in name]
        genetic_terms_found = [name for name in rule_names if "genetic" in name]
        biometric_terms_found = [name for name in rule_names if "biometric" in name]

        assert len(health_terms_found) > 0
        assert len(genetic_terms_found) > 0
        assert len(biometric_terms_found) > 0

    def test_patterns_are_tuples_not_lists(self):
        """Test that all patterns are stored as tuples, not lists."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert isinstance(rule.patterns, tuple)
            assert not isinstance(rule.patterns, list)

    def test_risk_level_distribution(self):
        """Test that we have a reasonable distribution of risk levels."""
        rules = self.ruleset.get_rules()
        risk_counts = {"low": 0, "medium": 0, "high": 0}

        for rule in rules:
            risk_counts[rule.risk_level] += 1

        # We should have rules at medium and high risk levels
        assert risk_counts["medium"] > 0
        assert risk_counts["high"] > 0

        # Total should match expected
        assert sum(risk_counts.values()) == len(rules)

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


class TestPersonalDataIntegration:
    """Integration tests for PersonalDataRuleset with other components."""

    def test_ruleset_can_be_used_with_registry(self):
        """Test that PersonalDataRuleset works with the registry pattern."""
        # Reset singleton to avoid conflicts
        RulesetRegistry._instance = None  # type: ignore[attr-defined]

        registry = RulesetRegistry()
        registry.register("test_personal_data", PersonalDataRuleset)

        # Should be able to retrieve and instantiate
        ruleset_class = registry.get_ruleset_class("test_personal_data")
        assert ruleset_class is PersonalDataRuleset

        instance = ruleset_class()
        assert isinstance(instance, PersonalDataRuleset)
        assert instance.name == "personal_data"

    def test_ruleset_loader_integration(self):
        """Test that PersonalDataRuleset works with RulesetLoader."""
        # Reset singleton
        RulesetRegistry._instance = None  # type: ignore[attr-defined]

        registry = RulesetRegistry()
        registry.register("loader_test", PersonalDataRuleset)

        # Load via RulesetLoader
        rules = RulesetLoader.load_ruleset("loader_test")

        assert isinstance(rules, tuple)
        assert len(rules) > 0
        assert all(isinstance(rule, Rule) for rule in rules)

        # Should have the same rules as direct instantiation
        direct_rules = PersonalDataRuleset().get_rules()
        assert len(rules) == len(direct_rules)
