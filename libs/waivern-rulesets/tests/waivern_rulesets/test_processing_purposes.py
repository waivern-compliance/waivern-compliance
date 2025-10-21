"""Unit tests for ProcessingPurposesRuleset class."""

import pytest
from pydantic import ValidationError
from waivern_core import RuleComplianceData

from waivern_rulesets.base import RulesetLoader, RulesetRegistry
from waivern_rulesets.processing_purposes import (
    ProcessingPurposeRule,
    ProcessingPurposesRuleset,
    ProcessingPurposesRulesetData,
)


class TestProcessingPurposeRule:
    """Test cases for the ProcessingPurposeRule class."""

    def test_processing_purpose_rule_with_all_fields(self) -> None:
        """Test ProcessingPurposeRule with all fields."""
        rule = ProcessingPurposeRule(
            name="analytics_rule",
            description="Analytics processing rule",
            patterns=("analytics", "tracking"),
            purpose_category="analytics",
            risk_level="medium",
        )

        assert rule.name == "analytics_rule"
        assert rule.purpose_category == "analytics"
        assert rule.risk_level == "medium"


class TestProcessingPurposesRulesetData:
    """Test cases for the ProcessingPurposesRulesetData class."""

    def test_processing_purposes_ruleset_validation(self) -> None:
        """Test ProcessingPurposesRulesetData validates categories correctly."""
        rule = ProcessingPurposeRule(
            name="test_rule",
            description="Test rule",
            patterns=("test",),
            purpose_category="ANALYTICS",
            risk_level="medium",
        )

        ruleset = ProcessingPurposesRulesetData(
            name="test_ruleset",
            version="1.0.0",
            description="Test ruleset",
            purpose_categories=["ANALYTICS", "OPERATIONAL"],
            sensitive_categories=["ANALYTICS"],
            rules=[rule],
        )

        assert len(ruleset.rules) == 1
        assert "ANALYTICS" in ruleset.sensitive_categories
        assert "OPERATIONAL" in ruleset.purpose_categories

    def test_processing_purposes_ruleset_invalid_category(self) -> None:
        """Test ProcessingPurposesRulesetData rejects invalid rule categories."""
        rule = ProcessingPurposeRule(
            name="test_rule",
            description="Test rule",
            patterns=("test",),
            purpose_category="INVALID_CATEGORY",
            risk_level="medium",
        )

        with pytest.raises(ValidationError, match="invalid purpose_category"):
            ProcessingPurposesRulesetData(
                name="test_ruleset",
                version="1.0.0",
                description="Test ruleset",
                purpose_categories=["ANALYTICS", "OPERATIONAL"],
                rules=[rule],
            )

    def test_processing_purposes_sensitive_categories_subset_validation(self) -> None:
        """Test sensitive_categories must be subset of purpose_categories."""
        with pytest.raises(
            ValidationError, match="must be subset of purpose_categories"
        ):
            ProcessingPurposesRulesetData(
                name="test_ruleset",
                version="1.0.0",
                description="Test ruleset",
                purpose_categories=["ANALYTICS"],
                sensitive_categories=["INVALID_SENSITIVE"],
                rules=[],
            )


class TestProcessingPurposesRuleset:
    """Test cases for the ProcessingPurposesRuleset class."""

    def setup_method(self) -> None:
        """Set up test fixtures for each test method."""
        self.ruleset = ProcessingPurposesRuleset()

    def test_name_property_returns_canonical_name(self) -> None:
        """Test ProcessingPurposesRuleset returns canonical name."""
        ruleset = ProcessingPurposesRuleset()

        assert ruleset.name == "processing_purposes"

    def test_version_property_returns_correct_string_format(self) -> None:
        """Test that version property returns a non-empty string."""
        version = self.ruleset.version

        assert isinstance(version, str)
        assert len(version) > 0
        # Version should follow semantic versioning pattern (x.y.z)
        parts = version.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)

    def test_get_rules_returns_tuple_of_rules(self) -> None:
        """Test that get_rules returns an immutable tuple of Rule objects."""
        rules = self.ruleset.get_rules()

        assert isinstance(rules, tuple)
        assert len(rules) > 0
        assert all(isinstance(rule, ProcessingPurposeRule) for rule in rules)

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
            assert hasattr(rule, "purpose_category")

            assert isinstance(rule.name, str)
            assert isinstance(rule.description, str)
            assert isinstance(rule.patterns, tuple)
            assert isinstance(rule.risk_level, str)
            assert isinstance(rule.purpose_category, str)

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

    def test_rules_have_purpose_category_field(self) -> None:
        """Test that all rules have purpose_category field."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert isinstance(rule.purpose_category, str)
            assert len(rule.purpose_category) > 0

    def test_rules_have_compliance_information(self) -> None:
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


class TestProcessingPurposesIntegration:
    """Integration tests for ProcessingPurposesRuleset with other components."""

    def test_ruleset_can_be_used_with_registry(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that ProcessingPurposesRuleset works with the registry pattern."""
        isolated_registry.clear()
        isolated_registry.register(
            "test_processing_purposes", ProcessingPurposesRuleset, ProcessingPurposeRule
        )

        # Should be able to retrieve and instantiate
        ruleset_class = isolated_registry.get_ruleset_class(
            "test_processing_purposes", ProcessingPurposeRule
        )
        assert ruleset_class is ProcessingPurposesRuleset

        instance = ruleset_class()
        assert isinstance(instance, ProcessingPurposesRuleset)
        assert instance.name == "processing_purposes"

    def test_ruleset_loader_integration(
        self, isolated_registry: RulesetRegistry
    ) -> None:
        """Test that ProcessingPurposesRuleset works with RulesetLoader."""
        isolated_registry.clear()
        isolated_registry.register(
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
