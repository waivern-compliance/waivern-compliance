"""Unit tests for GDPR data subject classification ruleset."""

import pytest
from pydantic import ValidationError

from waivern_rulesets import AbstractRuleset
from waivern_rulesets.gdpr_data_subject_classification import (
    GDPRDataSubjectClassificationRule,
    GDPRDataSubjectClassificationRuleset,
)
from waivern_rulesets.gdpr_data_subject_classification.ruleset import (
    GDPRDataSubjectClassificationRulesetData,
    RiskModifier,
)
from waivern_rulesets.testing import RulesetContractTests

# =============================================================================
# Contract Tests (inherited from RulesetContractTests)
# =============================================================================


class TestGDPRDataSubjectClassificationRulesetContract(
    RulesetContractTests[GDPRDataSubjectClassificationRule]
):
    """Contract tests for GDPRDataSubjectClassificationRuleset."""

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
# Model Validator Tests (our custom validation logic)
# =============================================================================


class TestGDPRDataSubjectClassificationRulesetDataValidation:
    """Test our custom model validators on the ruleset data class."""

    def test_rejects_invalid_data_subject_category(self) -> None:
        """Test that rules with data_subject_category not in master list are rejected."""
        rule = GDPRDataSubjectClassificationRule(
            name="Invalid Rule",
            description="Test",
            data_subject_category="invalid_category",
            article_references=("Article 4(1)",),
            typical_lawful_bases=("contract",),
            indicator_categories=("employee",),
        )

        with pytest.raises(ValidationError, match="invalid data_subject_category"):
            GDPRDataSubjectClassificationRulesetData(
                name="test",
                version="1.0.0",
                description="Test",
                default_article_references=["Article 4(1)"],
                data_subject_categories=["employee"],
                indicator_categories=["employee"],
                rules=[rule],
            )

    def test_rejects_invalid_indicator_categories(self) -> None:
        """Test that rules with indicator_categories not in master list are rejected."""
        rule = GDPRDataSubjectClassificationRule(
            name="Invalid Rule",
            description="Test",
            data_subject_category="employee",
            article_references=("Article 4(1)",),
            typical_lawful_bases=("contract",),
            indicator_categories=("invalid_indicator",),
        )

        with pytest.raises(ValidationError, match="invalid indicator_categories"):
            GDPRDataSubjectClassificationRulesetData(
                name="test",
                version="1.0.0",
                description="Test",
                default_article_references=["Article 4(1)"],
                data_subject_categories=["employee"],
                indicator_categories=["employee"],
                rules=[rule],
            )


class TestRiskModifierValidation:
    """Test our custom model validator on RiskModifier."""

    def test_requires_at_least_one_pattern(self) -> None:
        """Test that RiskModifier requires at least one pattern type."""
        with pytest.raises(ValidationError, match="must have at least one pattern"):
            RiskModifier(
                patterns=[],
                value_patterns=[],
                modifier="test_modifier",
                article_references=["Article 8"],
            )
