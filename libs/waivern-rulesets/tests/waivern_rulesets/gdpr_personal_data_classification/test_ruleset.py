"""Unit tests for GDPR personal data classification ruleset."""

import pytest
from pydantic import ValidationError

from waivern_rulesets import AbstractRuleset
from waivern_rulesets.gdpr_personal_data_classification import (
    GDPRPersonalDataClassificationRule,
    GDPRPersonalDataClassificationRuleset,
    GDPRPersonalDataClassificationRulesetData,
)
from waivern_rulesets.testing import RulesetContractTests

# =============================================================================
# Contract Tests (inherited from RulesetContractTests)
# =============================================================================


class TestGDPRPersonalDataClassificationRulesetContract(
    RulesetContractTests[GDPRPersonalDataClassificationRule]
):
    """Contract tests for GDPRPersonalDataClassificationRuleset."""

    @pytest.fixture
    def ruleset_class(
        self,
    ) -> type[AbstractRuleset[GDPRPersonalDataClassificationRule]]:
        """Provide the ruleset class to test."""
        return GDPRPersonalDataClassificationRuleset

    @pytest.fixture
    def rule_class(self) -> type[GDPRPersonalDataClassificationRule]:
        """Provide the rule class used by the ruleset."""
        return GDPRPersonalDataClassificationRule

    @pytest.fixture
    def expected_name(self) -> str:
        """Provide the expected canonical name of the ruleset."""
        return "gdpr_personal_data_classification"


# =============================================================================
# Field Validator Tests (our custom code)
# =============================================================================


class TestGDPRPersonalDataClassificationRule:
    """Test our custom field validators on the rule class."""

    def test_indicator_categories_converted_from_list_to_tuple(self) -> None:
        """Test that indicator_categories list is converted to tuple for immutability."""
        indicator_cats: list[str] = ["payment", "financial"]
        rule = GDPRPersonalDataClassificationRule(
            name="Test Classification",
            description="Test rule",
            privacy_category="financial_data",
            indicator_categories=indicator_cats,  # type: ignore[arg-type]
        )

        assert isinstance(rule.indicator_categories, tuple)
        assert rule.indicator_categories == ("payment", "financial")


# =============================================================================
# Model Validator Tests (our custom validation logic)
# =============================================================================


class TestGDPRPersonalDataClassificationRulesetDataValidation:
    """Test our custom model validators on the ruleset data class."""

    def test_rejects_invalid_privacy_category(self) -> None:
        """Test that rules with privacy_category not in master list are rejected."""
        rule = GDPRPersonalDataClassificationRule(
            name="Invalid Category Rule",
            description="Rule with invalid privacy_category",
            privacy_category="invalid_type",
            indicator_categories=("email",),
        )

        with pytest.raises(ValidationError, match="invalid privacy_category"):
            GDPRPersonalDataClassificationRulesetData(
                name="test_ruleset",
                version="1.0.0",
                description="Test ruleset",
                privacy_categories=["health_data", "identification_data"],
                indicator_categories=["email"],
                rules=[rule],
            )

    def test_rejects_invalid_indicator_categories(self) -> None:
        """Test that rules with indicator_categories not in master list are rejected."""
        rule = GDPRPersonalDataClassificationRule(
            name="Invalid Categories Rule",
            description="Rule with invalid indicator categories",
            privacy_category="health_data",
            indicator_categories=("invalid_category",),
        )

        with pytest.raises(ValidationError, match="invalid indicator_categories"):
            GDPRPersonalDataClassificationRulesetData(
                name="test_ruleset",
                version="1.0.0",
                description="Test ruleset",
                privacy_categories=["health_data"],
                indicator_categories=["email", "health"],
                rules=[rule],
            )


# =============================================================================
# Business Rule Tests (actual YAML data)
# =============================================================================


class TestGDPRPersonalDataClassificationRulesetBusinessRules:
    """Test business rules in the actual YAML ruleset data."""

    def test_special_category_rules_have_article_9_references(self) -> None:
        """Test that special category rules reference Article 9."""
        ruleset = GDPRPersonalDataClassificationRuleset()
        rules = ruleset.get_rules()

        for rule in rules:
            if rule.special_category:
                article_refs = " ".join(rule.article_references)
                assert "Article 9" in article_refs or "9" in article_refs
