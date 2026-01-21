"""Unit tests for GDPR data subject classification ruleset."""

import tempfile
from unittest.mock import patch

import pytest
import yaml
from pydantic import ValidationError

from waivern_rulesets import AbstractRuleset
from waivern_rulesets.gdpr_data_subject_classification import (
    GDPRDataSubjectClassificationRule,
    GDPRDataSubjectClassificationRuleset,
    GDPRDataSubjectClassificationRulesetData,
    RiskModifier,
    RiskModifiers,
)
from waivern_rulesets.testing import RulesetContractTests

# =============================================================================
# Contract Tests (inherited from RulesetContractTests)
# =============================================================================


class TestGDPRDataSubjectClassificationRulesetContract(
    RulesetContractTests[GDPRDataSubjectClassificationRule]
):
    """Contract tests for GDPRDataSubjectClassificationRuleset.

    Inherits all standard ruleset contract tests automatically.

    """

    @pytest.fixture
    def ruleset_class(
        self,
    ) -> type[AbstractRuleset[GDPRDataSubjectClassificationRule]]:
        """Provide the ruleset class to test."""
        return GDPRDataSubjectClassificationRuleset

    @pytest.fixture
    def rule_class(self) -> type[GDPRDataSubjectClassificationRule]:
        """Provide the rule class used by the ruleset."""
        return GDPRDataSubjectClassificationRule

    @pytest.fixture
    def expected_name(self) -> str:
        """Provide the expected canonical name of the ruleset."""
        return "gdpr_data_subject_classification"


# =============================================================================
# Rule-specific Tests (unique to GDPRDataSubjectClassificationRule)
# =============================================================================


class TestGDPRDataSubjectClassificationRule:
    """Test cases for the GDPRDataSubjectClassificationRule class."""

    def test_rule_with_all_fields(self) -> None:
        """Test rule with all fields."""
        rule = GDPRDataSubjectClassificationRule(
            name="Employees",
            description="Current and former employees",
            data_subject_category="employee",
            article_references=["Article 4(1)", "Article 6(1)(b)"],
            typical_lawful_bases=("contract", "legal_obligation"),
            indicator_categories=("employee", "former_employee", "contractor"),
        )

        assert rule.name == "Employees"
        assert rule.data_subject_category == "employee"
        assert rule.article_references == ["Article 4(1)", "Article 6(1)(b)"]
        assert rule.typical_lawful_bases == ("contract", "legal_obligation")
        assert rule.indicator_categories == (
            "employee",
            "former_employee",
            "contractor",
        )

    def test_rule_converts_lists_to_tuples(self) -> None:
        """Test that list fields are converted to tuples for immutability."""
        rule = GDPRDataSubjectClassificationRule(
            name="Test Rule",
            description="Test",
            data_subject_category="customer",
            article_references=["Article 4(1)"],
            typical_lawful_bases=["contract"],  # type: ignore[arg-type] # Test list→tuple conversion
            indicator_categories=["customer"],  # type: ignore[arg-type] # Test list→tuple conversion
        )

        assert isinstance(rule.typical_lawful_bases, tuple)
        assert isinstance(rule.indicator_categories, tuple)

    def test_rule_requires_at_least_one_typical_lawful_basis(self) -> None:
        """Test that rule requires at least one typical lawful basis."""
        with pytest.raises(ValidationError, match="at least 1 item"):
            GDPRDataSubjectClassificationRule(
                name="Invalid Rule",
                description="Test",
                data_subject_category="customer",
                article_references=["Article 4(1)"],
                typical_lawful_bases=[],  # type: ignore[arg-type] # Empty - invalid
                indicator_categories=["customer"],  # type: ignore[arg-type]
            )

    def test_rule_requires_at_least_one_indicator_category(self) -> None:
        """Test that rule requires at least one indicator category."""
        with pytest.raises(ValidationError, match="at least 1 item"):
            GDPRDataSubjectClassificationRule(
                name="Invalid Rule",
                description="Test",
                data_subject_category="customer",
                article_references=["Article 4(1)"],
                typical_lawful_bases=["contract"],  # type: ignore[arg-type]
                indicator_categories=[],  # type: ignore[arg-type] # Empty - invalid
            )


# =============================================================================
# RiskModifier Tests
# =============================================================================


class TestRiskModifiers:
    """Test cases for RiskModifier and RiskModifiers classes."""

    def test_risk_modifier_with_all_fields(self) -> None:
        """Test RiskModifier with patterns and value_patterns fields."""
        modifier = RiskModifier(
            patterns=["minor", "child"],
            value_patterns=["under.*years"],
            modifier="minor",
            article_references=["Article 8"],
        )

        assert modifier.patterns == ["minor", "child"]
        assert modifier.value_patterns == ["under.*years"]
        assert modifier.modifier == "minor"
        assert modifier.article_references == ["Article 8"]

    def test_risk_modifier_with_patterns_only(self) -> None:
        """Test RiskModifier with only word boundary patterns."""
        modifier = RiskModifier(
            patterns=["vulnerable"],
            modifier="vulnerable_individual",
            article_references=["Recital 75"],
        )

        assert modifier.patterns == ["vulnerable"]
        assert modifier.value_patterns == []

    def test_risk_modifier_with_value_patterns_only(self) -> None:
        """Test RiskModifier with only regex patterns."""
        modifier = RiskModifier(
            value_patterns=["third.country"],
            modifier="non_eu_resident",
            article_references=["Article 3"],
        )

        assert modifier.patterns == []
        assert modifier.value_patterns == ["third.country"]

    def test_risk_modifier_requires_at_least_one_pattern(self) -> None:
        """Test that RiskModifier requires at least one pattern type."""
        with pytest.raises(ValidationError, match="must have at least one pattern"):
            RiskModifier(
                patterns=[],
                value_patterns=[],
                modifier="test_modifier",
                article_references=["Article 8"],
            )

    def test_risk_modifier_requires_article_references(self) -> None:
        """Test that RiskModifier requires at least one article reference."""
        with pytest.raises(ValidationError, match="at least 1 item"):
            RiskModifier(
                patterns=["test"],
                modifier="test_modifier",
                article_references=[],  # Empty - invalid
            )

    def test_risk_modifiers_container(self) -> None:
        """Test RiskModifiers container."""
        modifiers = RiskModifiers(
            risk_increasing=[
                RiskModifier(
                    patterns=["minor"],
                    modifier="minor",
                    article_references=["Article 8"],
                ),
            ],
            risk_decreasing=[
                RiskModifier(
                    patterns=["non-EU"],
                    modifier="non_eu_resident",
                    article_references=["Article 3"],
                ),
            ],
        )

        assert len(modifiers.risk_increasing) == 1
        assert len(modifiers.risk_decreasing) == 1
        assert modifiers.risk_increasing[0].modifier == "minor"

    def test_risk_modifiers_defaults_to_empty(self) -> None:
        """Test RiskModifiers defaults to empty lists."""
        modifiers = RiskModifiers()

        assert modifiers.risk_increasing == []
        assert modifiers.risk_decreasing == []


# =============================================================================
# RulesetData Validation Tests
# =============================================================================


class TestGDPRDataSubjectClassificationRulesetData:
    """Test cases for the GDPRDataSubjectClassificationRulesetData class."""

    def test_ruleset_data_with_all_fields(self) -> None:
        """Test ruleset data with all fields."""
        rule = GDPRDataSubjectClassificationRule(
            name="Employees",
            description="Current employees",
            data_subject_category="employee",
            article_references=["Article 4(1)"],
            typical_lawful_bases=("contract",),
            indicator_categories=("employee",),
        )

        ruleset_data = GDPRDataSubjectClassificationRulesetData(
            name="gdpr_data_subject_classification",
            version="1.0.0",
            description="GDPR data subject classification",
            default_article_references=["Article 4(1)", "Article 30(1)(c)"],
            data_subject_categories=["employee", "customer"],
            indicator_categories=["employee", "customer"],
            risk_modifiers=RiskModifiers(),
            rules=[rule],
        )

        assert len(ruleset_data.rules) == 1
        assert "employee" in ruleset_data.data_subject_categories

    def test_ruleset_data_rejects_invalid_data_subject_category(self) -> None:
        """Test that ruleset data rejects rules with invalid data subject categories."""
        rule = GDPRDataSubjectClassificationRule(
            name="Invalid Rule",
            description="Test",
            data_subject_category="invalid_category",  # Not in master list
            article_references=["Article 4(1)"],
            typical_lawful_bases=("contract",),
            indicator_categories=("employee",),
        )

        with pytest.raises(ValidationError, match="invalid data_subject_category"):
            GDPRDataSubjectClassificationRulesetData(
                name="test",
                version="1.0.0",
                description="Test",
                default_article_references=["Article 4(1)"],
                data_subject_categories=["employee"],  # Missing 'invalid_category'
                indicator_categories=["employee"],
                rules=[rule],
            )

    def test_ruleset_data_rejects_invalid_indicator_categories(self) -> None:
        """Test that ruleset data rejects rules with invalid indicator categories."""
        rule = GDPRDataSubjectClassificationRule(
            name="Invalid Rule",
            description="Test",
            data_subject_category="employee",
            article_references=["Article 4(1)"],
            typical_lawful_bases=("contract",),
            indicator_categories=("invalid_indicator",),  # Not in master list
        )

        with pytest.raises(ValidationError, match="invalid indicator_categories"):
            GDPRDataSubjectClassificationRulesetData(
                name="test",
                version="1.0.0",
                description="Test",
                default_article_references=["Article 4(1)"],
                data_subject_categories=["employee"],
                indicator_categories=["employee"],  # Missing 'invalid_indicator'
                rules=[rule],
            )


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestGDPRDataSubjectClassificationRulesetErrorHandling:
    """Error handling tests for GDPRDataSubjectClassificationRuleset."""

    def test_get_rules_missing_yaml_file_error(self) -> None:
        """Test FileNotFoundError when YAML file doesn't exist."""
        with patch("pathlib.Path.open", side_effect=FileNotFoundError("No such file")):
            ruleset = GDPRDataSubjectClassificationRuleset()
            with pytest.raises(FileNotFoundError):
                ruleset.get_rules()

    def test_get_rules_invalid_yaml_content_error(self) -> None:
        """Test error handling for malformed YAML syntax."""
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml") as f:
            f.write("invalid: yaml: content[\nbroken syntax")
            f.seek(0)
            with patch("pathlib.Path.open", return_value=f):
                ruleset = GDPRDataSubjectClassificationRuleset()
                with pytest.raises(yaml.YAMLError):
                    ruleset.get_rules()

    def test_get_rules_yaml_validation_error(self) -> None:
        """Test error handling for YAML that fails Pydantic validation."""
        invalid_yaml_content = """name: "gdpr_data_subject_classification"
version: "1.0.0"
description: "Test ruleset"
default_article_references:
  - "Article 4(1)"
data_subject_categories:
  - "employee"
indicator_categories:
  - "employee"
rules: []
"""
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml") as f:
            f.write(invalid_yaml_content)
            f.seek(0)
            with patch("pathlib.Path.open", return_value=f):
                ruleset = GDPRDataSubjectClassificationRuleset()
                with pytest.raises(ValidationError):
                    ruleset.get_rules()
