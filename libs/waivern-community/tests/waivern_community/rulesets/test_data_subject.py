"""Unit tests for data subject rule types."""

import tempfile
from unittest.mock import patch

import pytest
import yaml
from pydantic import ValidationError

from waivern_community.rulesets.base import RulesetLoader, RulesetRegistry
from waivern_community.rulesets.data_subjects import (
    DataSubjectRule,
    DataSubjectRulesetData,
    DataSubjectsRuleset,
)


class TestDataSubjectRule:
    """Test cases for the DataSubjectRule class."""

    def test_data_subject_rule_with_all_fields(self):
        """Test DataSubjectRule with all fields."""
        rule = DataSubjectRule(
            name="employee_rule",
            description="Employee detection rule",
            patterns=("employee", "staff"),
            subject_category="employee",
            indicator_type="primary",
            confidence_weight=40,
            applicable_contexts=["database", "source_code"],
            risk_level="medium",
        )

        assert rule.name == "employee_rule"
        assert rule.subject_category == "employee"
        assert rule.indicator_type == "primary"
        assert rule.confidence_weight == 40
        assert rule.applicable_contexts == ["database", "source_code"]

    def test_data_subject_rule_confidence_weight_validation(self):
        """Test DataSubjectRule confidence_weight constraints."""
        # Test minimum bound
        with pytest.raises(
            ValidationError, match="Input should be greater than or equal to 1"
        ):
            DataSubjectRule(
                name="invalid_rule",
                description="Rule with invalid weight",
                patterns=("test",),
                subject_category="employee",
                indicator_type="primary",
                confidence_weight=0,  # Invalid: below minimum
                applicable_contexts=["database"],
                risk_level="low",
            )

        # Test maximum bound
        with pytest.raises(
            ValidationError, match="Input should be less than or equal to 50"
        ):
            DataSubjectRule(
                name="invalid_rule",
                description="Rule with invalid weight",
                patterns=("test",),
                subject_category="employee",
                indicator_type="primary",
                confidence_weight=51,  # Invalid: above maximum
                applicable_contexts=["database"],
                risk_level="low",
            )

    def test_data_subject_rule_indicator_type_validation(self):
        """Test DataSubjectRule indicator_type literal validation."""
        # Valid indicator types should work
        for indicator_type in ["primary", "secondary", "contextual"]:
            rule = DataSubjectRule(
                name=f"{indicator_type}_rule",
                description=f"{indicator_type} indicator rule",
                patterns=("test",),
                subject_category="employee",
                indicator_type=indicator_type,  # type: ignore
                confidence_weight=25,
                applicable_contexts=["database"],
                risk_level="low",
            )
            assert rule.indicator_type == indicator_type

        # Invalid indicator type should fail
        with pytest.raises(
            ValidationError,
            match="Input should be 'primary', 'secondary' or 'contextual'",
        ):
            DataSubjectRule(
                name="invalid_rule",
                description="Rule with invalid indicator type",
                patterns=("test",),
                subject_category="employee",
                indicator_type="invalid_type",  # Invalid literal value # type: ignore
                confidence_weight=25,
                applicable_contexts=["database"],
                risk_level="low",
            )


class TestDataSubjectRulesetData:
    """Test cases for the DataSubjectRulesetData class."""

    def test_data_subject_ruleset_with_all_fields(self):
        """Test DataSubjectRulesetData with all fields."""
        rule = DataSubjectRule(
            name="employee_rule",
            description="Employee detection rule",
            patterns=("employee", "staff"),
            subject_category="employee",
            indicator_type="primary",
            confidence_weight=40,
            applicable_contexts=["database"],
            risk_level="medium",
        )

        ruleset = DataSubjectRulesetData(
            name="data_subjects",
            version="1.0.0",
            description="Data subject classification ruleset",
            subject_categories=["employee", "customer", "prospect"],
            applicable_contexts=["database", "filesystem", "source_code"],
            risk_increasing_modifiers=["minor", "vulnerable group"],
            risk_decreasing_modifiers=["non-EU-resident"],
            rules=[rule],
        )

        assert len(ruleset.rules) == 1
        assert "employee" in ruleset.subject_categories
        assert "minor" in ruleset.risk_increasing_modifiers
        assert "non-EU-resident" in ruleset.risk_decreasing_modifiers

    def test_data_subject_ruleset_invalid_subject_category(self):
        """Test DataSubjectRulesetData rejects rules with invalid subject categories."""
        rule = DataSubjectRule(
            name="invalid_rule",
            description="Rule with invalid category",
            patterns=("test",),
            subject_category="invalid_category",  # Not in master list
            indicator_type="primary",
            confidence_weight=40,
            applicable_contexts=["database"],
            risk_level="medium",
        )

        with pytest.raises(ValidationError, match="invalid subject_category"):
            DataSubjectRulesetData(
                name="data_subjects",
                version="1.0.0",
                description="Data subject classification ruleset",
                subject_categories=["employee", "customer"],
                applicable_contexts=["database", "filesystem", "source_code"],
                risk_increasing_modifiers=["minor", "vulnerable group"],
                risk_decreasing_modifiers=["non-EU-resident"],
                rules=[rule],
            )

    def test_data_subject_ruleset_modifiers_validation(self):
        """Test DataSubjectRulesetData validates modifiers."""
        # Create dummy rule to satisfy minimum rule requirement
        rule = DataSubjectRule(
            name="dummy_rule",
            description="Dummy rule for modifier testing",
            patterns=("test",),
            subject_category="employee",
            indicator_type="primary",
            confidence_weight=25,
            applicable_contexts=["database"],
            risk_level="low",
        )

        # Valid modifiers should work
        ruleset = DataSubjectRulesetData(
            name="data_subjects",
            version="1.0.0",
            description="Test ruleset",
            subject_categories=["employee"],
            applicable_contexts=["database", "filesystem", "source_code"],
            risk_increasing_modifiers=["minor", "vulnerable group"],
            risk_decreasing_modifiers=["non-EU-resident"],
            rules=[rule],
        )
        assert "minor" in ruleset.risk_increasing_modifiers
        assert "vulnerable group" in ruleset.risk_increasing_modifiers
        assert "non-EU-resident" in ruleset.risk_decreasing_modifiers

    def test_data_subject_ruleset_duplicate_rule_names(self):
        """Test DataSubjectRulesetData rejects duplicate rule names."""
        rule1 = DataSubjectRule(
            name="duplicate_name",
            description="First rule",
            patterns=("test1",),
            subject_category="employee",
            indicator_type="primary",
            confidence_weight=40,
            applicable_contexts=["database"],
            risk_level="medium",
        )

        rule2 = DataSubjectRule(
            name="duplicate_name",  # Same name as rule1
            description="Second rule",
            patterns=("test2",),
            subject_category="customer",
            indicator_type="secondary",
            confidence_weight=20,
            applicable_contexts=["database", "filesystem"],
            risk_level="low",
        )

        with pytest.raises(ValidationError, match="Duplicate rule names found"):
            DataSubjectRulesetData(
                name="data_subjects",
                version="1.0.0",
                description="Test ruleset",
                subject_categories=["employee", "customer"],
                applicable_contexts=["database", "filesystem", "source_code"],
                risk_increasing_modifiers=["minor", "vulnerable group"],
                risk_decreasing_modifiers=["non-EU-resident"],
                rules=[rule1, rule2],
            )

    def test_data_subject_ruleset_invalid_applicable_contexts(self):
        """Test DataSubjectRulesetData rejects rules with invalid applicable contexts."""
        rule = DataSubjectRule(
            name="invalid_context_rule",
            description="Rule with invalid context",
            patterns=("test",),
            subject_category="employee",
            indicator_type="primary",
            confidence_weight=40,
            applicable_contexts=["invalid_context"],  # Not in master list
            risk_level="medium",
        )

        with pytest.raises(ValidationError, match="invalid applicable_contexts"):
            DataSubjectRulesetData(
                name="data_subjects",
                version="1.0.0",
                description="Data subject classification ruleset",
                subject_categories=["employee", "customer"],
                applicable_contexts=["database", "filesystem", "source_code"],
                risk_increasing_modifiers=["minor", "vulnerable group"],
                risk_decreasing_modifiers=["non-EU-resident"],
                rules=[rule],
            )


class TestDataSubjectsRuleset:
    """Test cases for the DataSubjectsRuleset class."""

    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.ruleset = DataSubjectsRuleset()

    def test_name_property_returns_canonical_name(self):
        """Test DataSubjectsRuleset returns canonical name."""
        ruleset = DataSubjectsRuleset()
        assert ruleset.name == "data_subjects"

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
        assert all(isinstance(rule, DataSubjectRule) for rule in rules)

    def test_get_rules_returns_consistent_count(self):
        """Test that get_rules returns a consistent number of rules."""
        rules1 = self.ruleset.get_rules()
        rules2 = self.ruleset.get_rules()
        assert len(rules1) == len(rules2)

    def test_get_rules_returns_same_tuple_each_time(self):
        """Test that get_rules returns the same immutable tuple instance each time."""
        rules1 = self.ruleset.get_rules()
        rules2 = self.ruleset.get_rules()
        assert rules1 is rules2  # Same tuple instance for immutability
        assert rules1 == rules2  # Same content

    def test_rules_are_immutable(self):
        """Test that returned rules tuple cannot be modified."""
        rules = self.ruleset.get_rules()
        assert isinstance(rules, tuple)
        # Attempting to modify should raise AttributeError
        with pytest.raises(AttributeError):
            rules.append(None)  # type: ignore[attr-defined]
        with pytest.raises(AttributeError):
            rules.clear()  # type: ignore[attr-defined]
        # Cannot assign to tuple elements
        with pytest.raises(TypeError):
            rules[0] = None  # type: ignore[index]

    def test_rule_names_are_unique(self):
        """Test that all rule names are unique."""
        rules = self.ruleset.get_rules()
        rule_names = [rule.name for rule in rules]
        assert len(rule_names) == len(set(rule_names))


class TestDataSubjectsRulesetIntegration:
    """Integration tests for DataSubjectsRuleset with other components."""

    def setup_method(self):
        """Reset the singleton registry before each test."""
        registry = RulesetRegistry()
        registry.clear()

    def teardown_method(self):
        """Clear registry after each test to prevent side effects."""
        registry = RulesetRegistry()
        registry.clear()

    def test_ruleset_can_be_used_with_registry(self):
        """Test that DataSubjectsRuleset works with the registry pattern."""
        registry = RulesetRegistry()
        registry.register("test_data_subjects", DataSubjectsRuleset, DataSubjectRule)

        # Should be able to retrieve and instantiate
        ruleset_class = registry.get_ruleset_class(
            "test_data_subjects", DataSubjectRule
        )
        assert ruleset_class is DataSubjectsRuleset

        instance = ruleset_class()
        assert isinstance(instance, DataSubjectsRuleset)
        assert instance.name == "data_subjects"

    def test_ruleset_loader_integration(self):
        """Test that DataSubjectsRuleset works with RulesetLoader."""
        registry = RulesetRegistry()
        registry.register("loader_test", DataSubjectsRuleset, DataSubjectRule)

        # Load via RulesetLoader
        rules = RulesetLoader.load_ruleset("loader_test", DataSubjectRule)

        assert isinstance(rules, tuple)
        assert len(rules) > 0
        assert all(isinstance(rule, DataSubjectRule) for rule in rules)

        # Should have the same rules as direct instantiation
        direct_rules = DataSubjectsRuleset().get_rules()
        assert len(rules) == len(direct_rules)


class TestDataSubjectsRulesetErrorHandling:
    """Error handling tests for DataSubjectsRuleset file operations."""

    def test_get_rules_missing_yaml_file_error(self):
        """Test FileNotFoundError when YAML file doesn't exist."""
        with patch("pathlib.Path.open", side_effect=FileNotFoundError("No such file")):
            ruleset = DataSubjectsRuleset()
            with pytest.raises(FileNotFoundError):
                ruleset.get_rules()

    def test_get_rules_invalid_yaml_content_error(self):
        """Test error handling for malformed YAML syntax."""
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml") as f:
            f.write("invalid: yaml: content[\nbroken syntax")
            f.seek(0)
            with patch("pathlib.Path.open", return_value=f):
                ruleset = DataSubjectsRuleset()
                with pytest.raises(yaml.YAMLError):
                    ruleset.get_rules()

    def test_get_rules_yaml_validation_error(self):
        """Test error handling for YAML that fails Pydantic validation."""
        invalid_yaml_content = """name: "data_subjects"
version: "1.0.0"
description: "Test ruleset"
subject_categories:
  - "employee"
rules: []
"""
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml") as f:
            f.write(invalid_yaml_content)
            f.seek(0)
            with patch("pathlib.Path.open", return_value=f):
                ruleset = DataSubjectsRuleset()
                with pytest.raises(ValidationError):
                    ruleset.get_rules()
