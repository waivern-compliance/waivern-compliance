"""Unit tests for GDPRPersonalDataClassificationRuleset class."""

import pytest
from pydantic import ValidationError

from waivern_rulesets.base import AbstractRuleset
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
    """Contract tests for GDPRPersonalDataClassificationRuleset.

    Inherits all standard ruleset contract tests automatically:
    - test_name_property_returns_canonical_name
    - test_version_property_returns_valid_semantic_version
    - test_get_rules_returns_tuple_with_at_least_one_rule
    - test_get_rules_returns_consistent_count
    - test_get_rules_returns_same_tuple_each_time
    - test_rules_are_immutable
    - test_rule_names_are_unique
    - test_ruleset_can_be_used_with_registry
    - test_ruleset_loader_integration

    """

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
# Rule-specific Tests (unique to GDPRPersonalDataClassificationRule)
# =============================================================================


class TestGDPRPersonalDataClassificationRule:
    """Test cases for the GDPRPersonalDataClassificationRule class."""

    def test_rule_with_all_fields(self) -> None:
        """Test GDPRPersonalDataClassificationRule with all fields."""
        rule = GDPRPersonalDataClassificationRule(
            name="Health Data Classification",
            description="Classifies health-related personal data indicators",
            gdpr_data_type="health_data",
            special_category=True,
            article_references=("Article 9(1)", "Article 9(2)(h)"),
            lawful_bases=("consent", "vital_interests"),
            indicator_categories=("health_data", "medical_records"),
            risk_level="high",
        )

        assert rule.name == "Health Data Classification"
        assert rule.gdpr_data_type == "health_data"
        assert rule.special_category is True
        assert rule.article_references == ("Article 9(1)", "Article 9(2)(h)")
        assert rule.lawful_bases == ("consent", "vital_interests")
        assert rule.indicator_categories == ("health_data", "medical_records")
        assert rule.risk_level == "high"

    def test_special_category_defaults_to_false(self) -> None:
        """Test GDPRPersonalDataClassificationRule special_category defaults to False."""
        rule = GDPRPersonalDataClassificationRule(
            name="Basic Profile Classification",
            description="Classifies basic profile data",
            gdpr_data_type="identification_data",
            indicator_categories=("basic_profile",),
            risk_level="medium",
        )

        assert rule.special_category is False

    def test_article_references_defaults_to_empty_tuple(self) -> None:
        """Test GDPRPersonalDataClassificationRule article_references defaults to empty."""
        rule = GDPRPersonalDataClassificationRule(
            name="Test Classification",
            description="Test rule",
            gdpr_data_type="contact_data",
            indicator_categories=("email",),
            risk_level="low",
        )

        assert rule.article_references == ()

    def test_lawful_bases_defaults_to_empty_tuple(self) -> None:
        """Test GDPRPersonalDataClassificationRule lawful_bases defaults to empty."""
        rule = GDPRPersonalDataClassificationRule(
            name="Test Classification",
            description="Test rule",
            gdpr_data_type="contact_data",
            indicator_categories=("email",),
            risk_level="low",
        )

        assert rule.lawful_bases == ()

    def test_indicator_categories_converted_from_list_to_tuple(self) -> None:
        """Test that indicator_categories list is converted to tuple for immutability."""
        # Intentionally pass a list to test runtime conversion (validator converts to tuple)
        indicator_cats: list[str] = ["payment_data", "bank_account"]
        rule = GDPRPersonalDataClassificationRule(
            name="Test Classification",
            description="Test rule",
            gdpr_data_type="financial_data",
            indicator_categories=indicator_cats,  # type: ignore[arg-type]
            risk_level="high",
        )

        assert isinstance(rule.indicator_categories, tuple)
        assert rule.indicator_categories == ("payment_data", "bank_account")


# =============================================================================
# RulesetData Validation Tests (unique to GDPRPersonalDataClassificationRulesetData)
# =============================================================================


class TestGDPRPersonalDataClassificationRulesetData:
    """Test cases for the GDPRPersonalDataClassificationRulesetData class."""

    def test_validates_gdpr_data_types_against_master_list(self) -> None:
        """Test that rules with invalid gdpr_data_type are rejected."""
        rule = GDPRPersonalDataClassificationRule(
            name="Invalid Type Rule",
            description="Rule with invalid gdpr_data_type",
            gdpr_data_type="invalid_type",  # Not in master list
            indicator_categories=("basic_profile",),
            risk_level="medium",
        )

        with pytest.raises(ValidationError, match="invalid gdpr_data_type"):
            GDPRPersonalDataClassificationRulesetData(
                name="test_ruleset",
                version="1.0.0",
                description="Test ruleset",
                gdpr_data_type_categories=["health_data", "contact_data"],
                indicator_categories=["basic_profile"],
                rules=[rule],
            )

    def test_validates_special_category_types_subset(self) -> None:
        """Test special_category_types must be subset of gdpr_data_type_categories."""
        with pytest.raises(
            ValidationError, match="special_category_types must be subset"
        ):
            GDPRPersonalDataClassificationRulesetData(
                name="test_ruleset",
                version="1.0.0",
                description="Test ruleset",
                gdpr_data_type_categories=["health_data", "contact_data"],
                special_category_types=["invalid_special"],  # Not in master list
                indicator_categories=["basic_profile"],
                rules=[],
            )

    def test_validates_indicator_categories_against_master_list(self) -> None:
        """Test that rules with invalid indicator_categories are rejected."""
        rule = GDPRPersonalDataClassificationRule(
            name="Invalid Categories Rule",
            description="Rule with invalid indicator categories",
            gdpr_data_type="health_data",
            indicator_categories=("invalid_category",),  # Not in master list
            risk_level="high",
        )

        with pytest.raises(ValidationError, match="invalid indicator_categories"):
            GDPRPersonalDataClassificationRulesetData(
                name="test_ruleset",
                version="1.0.0",
                description="Test ruleset",
                gdpr_data_type_categories=["health_data"],
                indicator_categories=["basic_profile", "health_data"],
                rules=[rule],
            )

    def test_valid_ruleset_data_passes_validation(self) -> None:
        """Test that valid ruleset data passes all validation."""
        rule = GDPRPersonalDataClassificationRule(
            name="Health Classification",
            description="Classifies health data",
            gdpr_data_type="health_data",
            special_category=True,
            indicator_categories=("health_indicator",),
            risk_level="high",
        )

        ruleset_data = GDPRPersonalDataClassificationRulesetData(
            name="test_ruleset",
            version="1.0.0",
            description="Test ruleset",
            gdpr_data_type_categories=["health_data", "contact_data"],
            special_category_types=["health_data"],
            indicator_categories=["health_indicator", "basic_profile"],
            rules=[rule],
        )

        assert len(ruleset_data.rules) == 1
        assert ruleset_data.rules[0].name == "Health Classification"


# =============================================================================
# Ruleset-specific Tests (unique to GDPRPersonalDataClassificationRuleset)
# =============================================================================


class TestGDPRPersonalDataClassificationRuleset:
    """Test cases for GDPRPersonalDataClassificationRuleset-specific behaviour."""

    def setup_method(self) -> None:
        """Set up test fixtures for each test method."""
        self.ruleset = GDPRPersonalDataClassificationRuleset()

    def test_rules_have_valid_gdpr_data_types(self) -> None:
        """Test that all rules have non-empty gdpr_data_type."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert isinstance(rule.gdpr_data_type, str)
            assert len(rule.gdpr_data_type) > 0

    def test_rules_have_indicator_categories(self) -> None:
        """Test that all rules have at least one indicator category."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert isinstance(rule.indicator_categories, tuple)
            assert len(rule.indicator_categories) > 0

    def test_special_category_rules_have_article_9_references(self) -> None:
        """Test that special category rules reference Article 9."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            if rule.special_category:
                # Special category rules should reference Article 9
                article_refs = " ".join(rule.article_references)
                assert "Article 9" in article_refs or "9" in article_refs
