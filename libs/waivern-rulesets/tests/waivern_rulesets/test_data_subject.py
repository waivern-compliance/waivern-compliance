"""Unit tests for data subject rule types."""

import tempfile
from unittest.mock import patch

import pytest
import yaml
from pydantic import ValidationError

from waivern_rulesets.base import AbstractRuleset
from waivern_rulesets.data_subjects import (
    DataSubjectRule,
    DataSubjectRulesetData,
    DataSubjectsRuleset,
)
from waivern_rulesets.testing import RulesetContractTests

# =============================================================================
# Contract Tests (inherited from RulesetContractTests)
# =============================================================================


class TestDataSubjectsRulesetContract(RulesetContractTests[DataSubjectRule]):
    """Contract tests for DataSubjectsRuleset.

    Inherits all standard ruleset contract tests automatically.

    """

    @pytest.fixture
    def ruleset_class(self) -> type[AbstractRuleset[DataSubjectRule]]:
        """Provide the ruleset class to test."""
        return DataSubjectsRuleset

    @pytest.fixture
    def rule_class(self) -> type[DataSubjectRule]:
        """Provide the rule class used by the ruleset."""
        return DataSubjectRule

    @pytest.fixture
    def expected_name(self) -> str:
        """Provide the expected canonical name of the ruleset."""
        return "data_subjects"


# =============================================================================
# Rule-specific Tests (unique to DataSubjectRule)
# =============================================================================


class TestDataSubjectRule:
    """Test cases for the DataSubjectRule class."""

    def test_data_subject_rule_with_all_fields(self) -> None:
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

    def test_data_subject_rule_confidence_weight_validation(self) -> None:
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

    def test_data_subject_rule_indicator_type_validation(self) -> None:
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


# =============================================================================
# RulesetData Validation Tests
# =============================================================================


class TestDataSubjectRulesetData:
    """Test cases for the DataSubjectRulesetData class."""

    def test_data_subject_ruleset_with_all_fields(self) -> None:
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

    def test_data_subject_ruleset_invalid_subject_category(self) -> None:
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

    def test_data_subject_ruleset_modifiers_validation(self) -> None:
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

    def test_data_subject_ruleset_duplicate_rule_names(self) -> None:
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

    def test_data_subject_ruleset_invalid_applicable_contexts(self) -> None:
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


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestDataSubjectsRulesetErrorHandling:
    """Error handling tests for DataSubjectsRuleset file operations."""

    def test_get_rules_missing_yaml_file_error(self) -> None:
        """Test FileNotFoundError when YAML file doesn't exist."""
        with patch("pathlib.Path.open", side_effect=FileNotFoundError("No such file")):
            ruleset = DataSubjectsRuleset()
            with pytest.raises(FileNotFoundError):
                ruleset.get_rules()

    def test_get_rules_invalid_yaml_content_error(self) -> None:
        """Test error handling for malformed YAML syntax."""
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml") as f:
            f.write("invalid: yaml: content[\nbroken syntax")
            f.seek(0)
            with patch("pathlib.Path.open", return_value=f):
                ruleset = DataSubjectsRuleset()
                with pytest.raises(yaml.YAMLError):
                    ruleset.get_rules()

    def test_get_rules_yaml_validation_error(self) -> None:
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
