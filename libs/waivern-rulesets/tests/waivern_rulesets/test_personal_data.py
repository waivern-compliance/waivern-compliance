"""Unit tests for PersonalDataRuleset class."""

import pytest

from waivern_rulesets.base import RulesetLoader, RulesetRegistry
from waivern_rulesets.personal_data import (
    PersonalDataRule,
    PersonalDataRuleset,
)


class TestPersonalDataRule:
    """Test cases for the PersonalDataRule class."""

    def test_personal_data_rule_with_all_fields(self) -> None:
        """Test PersonalDataRule with all fields."""
        rule = PersonalDataRule(
            name="email_rule",
            description="Email detection rule",
            patterns=("email", "e_mail"),
            data_type="basic_profile",
            special_category=False,
            risk_level="medium",
        )

        assert rule.name == "email_rule"
        assert rule.special_category is False
        assert rule.risk_level == "medium"
        assert len(rule.compliance) == 0

    def test_personal_data_rule_special_category_default(self) -> None:
        """Test PersonalDataRule special_category defaults to False."""
        rule = PersonalDataRule(
            name="basic_rule",
            description="Basic rule",
            patterns=("test",),
            data_type="basic_profile",
            risk_level="low",
        )

        assert rule.special_category is False


class TestPersonalDataRuleset:
    """Test cases for the PersonalDataRuleset class."""

    def setup_method(self) -> None:
        """Set up test fixtures for each test method."""
        self.ruleset = PersonalDataRuleset()

    def test_name_property_returns_canonical_name(self) -> None:
        """Test PersonalDataRuleset returns canonical name."""
        ruleset = PersonalDataRuleset()

        assert ruleset.name == "personal_data"

    def test_version_property_returns_correct_string_format(self) -> None:
        """Test that version property returns a non-empty string."""
        version = self.ruleset.version

        assert isinstance(version, str)
        assert len(version) > 0
        # Version should follow semantic versioning pattern (x.y.z)
        parts = version.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)

    def test_get_rules_returns_tuple_of_rules_with_at_least_one_rule(self) -> None:
        """Test that get_rules returns an immutable tuple of Rule objects."""
        rules = self.ruleset.get_rules()

        assert isinstance(rules, tuple)
        assert len(rules) > 0
        assert all(isinstance(rule, PersonalDataRule) for rule in rules)

    def test_get_rules_returns_consistent_count(self) -> None:
        """Test that get_rules returns a consistent number of rules."""
        rules1 = self.ruleset.get_rules()
        rules2 = self.ruleset.get_rules()

        assert len(rules1) == len(rules2)

    def test_rule_names_are_unique(self) -> None:
        """Test that all rule names are unique."""
        rules = self.ruleset.get_rules()
        rule_names = [rule.name for rule in rules]

        assert len(rule_names) == len(set(rule_names))

    def test_rules_have_correct_structure(self) -> None:
        """Test that each rule has the correct structure and required fields."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert hasattr(rule, "name")
            assert hasattr(rule, "description")
            assert hasattr(rule, "patterns")
            assert hasattr(rule, "risk_level")
            assert hasattr(rule, "special_category")

            assert isinstance(rule.name, str)
            assert isinstance(rule.description, str)
            assert isinstance(rule.patterns, tuple)
            assert isinstance(rule.risk_level, str)
            assert isinstance(rule.special_category, bool)

    def test_rules_have_valid_risk_levels(self) -> None:
        """Test that all rules have valid risk levels."""
        rules = self.ruleset.get_rules()
        valid_risk_levels = {"low", "medium", "high"}

        for rule in rules:
            assert rule.risk_level in valid_risk_levels

    def test_rules_have_non_empty_patterns(self) -> None:
        """Test that all rules have non-empty pattern tuples."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert len(rule.patterns) > 0
            assert all(isinstance(pattern, str) for pattern in rule.patterns)
            assert all(len(pattern) > 0 for pattern in rule.patterns)

    def test_rules_have_non_empty_names_and_descriptions(self) -> None:
        """Test that all rules have non-empty names and descriptions."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert len(rule.name) > 0
            assert len(rule.description) > 0

    def test_patterns_are_tuples_not_lists(self) -> None:
        """Test that all patterns are stored as tuples, not lists."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert isinstance(rule.patterns, tuple)
            assert not isinstance(rule.patterns, list)

    def test_risk_level_distribution(self) -> None:
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

    def test_get_rules_returns_same_tuple_each_time(self) -> None:
        """Test that get_rules returns the same immutable tuple instance each time."""
        rules1 = self.ruleset.get_rules()
        rules2 = self.ruleset.get_rules()

        assert rules1 is rules2  # Same tuple instance for immutability
        assert rules1 == rules2  # Same content

    def test_rules_are_immutable(self) -> None:
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

    def test_ruleset_can_be_used_with_registry(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that PersonalDataRuleset works with the registry pattern."""
        isolated_registry.clear()
        isolated_registry.register(
            "test_personal_data", PersonalDataRuleset, PersonalDataRule
        )

        # Should be able to retrieve and instantiate
        ruleset_class = isolated_registry.get_ruleset_class(
            "test_personal_data", PersonalDataRule
        )
        assert ruleset_class is PersonalDataRuleset

        instance = ruleset_class()
        assert isinstance(instance, PersonalDataRuleset)
        assert instance.name == "personal_data"

    def test_ruleset_loader_integration(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that PersonalDataRuleset works with RulesetLoader."""
        isolated_registry.clear()
        isolated_registry.register("loader_test", PersonalDataRuleset, PersonalDataRule)

        # Load via RulesetLoader
        rules = RulesetLoader.load_ruleset("loader_test", PersonalDataRule)

        assert isinstance(rules, tuple)
        assert len(rules) > 0
        assert all(isinstance(rule, PersonalDataRule) for rule in rules)

        # Should have the same rules as direct instantiation
        direct_rules = PersonalDataRuleset().get_rules()
        assert len(rules) == len(direct_rules)
