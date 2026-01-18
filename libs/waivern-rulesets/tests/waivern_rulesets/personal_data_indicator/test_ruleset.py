"""Unit tests for PersonalDataIndicatorRuleset class."""

import pytest
from pydantic import ValidationError

from waivern_rulesets import AbstractRuleset
from waivern_rulesets.personal_data_indicator import (
    PersonalDataIndicatorRule,
    PersonalDataIndicatorRuleset,
    PersonalDataIndicatorRulesetData,
)
from waivern_rulesets.testing import RulesetContractTests

# =============================================================================
# Contract Tests (inherited from RulesetContractTests)
# =============================================================================


class TestPersonalDataIndicatorRulesetContract(
    RulesetContractTests[PersonalDataIndicatorRule]
):
    """Contract tests for PersonalDataIndicatorRuleset.

    Inherits all standard ruleset contract tests automatically.

    """

    @pytest.fixture
    def ruleset_class(self) -> type[AbstractRuleset[PersonalDataIndicatorRule]]:
        """Provide the ruleset class to test."""
        return PersonalDataIndicatorRuleset

    @pytest.fixture
    def rule_class(self) -> type[PersonalDataIndicatorRule]:
        """Provide the rule class used by the ruleset."""
        return PersonalDataIndicatorRule

    @pytest.fixture
    def expected_name(self) -> str:
        """Provide the expected canonical name of the ruleset."""
        return "personal_data_indicator"


# =============================================================================
# Rule-specific Tests (unique to PersonalDataIndicatorRule)
# =============================================================================


class TestPersonalDataIndicatorRule:
    """Test cases for the PersonalDataIndicatorRule class."""

    def test_personal_data_indicator_rule_with_all_fields(self) -> None:
        """Test PersonalDataIndicatorRule with all fields."""
        rule = PersonalDataIndicatorRule(
            name="email_rule",
            description="Email detection rule",
            patterns=("email", "e_mail"),
            category="basic_profile",
        )

        assert rule.name == "email_rule"
        assert rule.description == "Email detection rule"
        assert rule.patterns == ("email", "e_mail")
        assert rule.category == "basic_profile"

    def test_personal_data_indicator_rule_is_framework_agnostic(self) -> None:
        """Test PersonalDataIndicatorRule does not have GDPR-specific fields."""
        rule = PersonalDataIndicatorRule(
            name="test_rule",
            description="Test rule",
            patterns=("test",),
            category="basic_profile",
        )

        # Verify no special_category field exists
        assert not hasattr(rule, "special_category")
        # Verify category is the generic field, not data_type
        assert hasattr(rule, "category")


# =============================================================================
# RulesetData Validation Tests
# =============================================================================


class TestPersonalDataIndicatorRulesetData:
    """Test cases for the PersonalDataIndicatorRulesetData class."""

    def test_ruleset_data_with_valid_category(self) -> None:
        """Test PersonalDataIndicatorRulesetData with valid rule categories."""
        rule = PersonalDataIndicatorRule(
            name="email_rule",
            description="Email detection",
            patterns=("email",),
            category="email",
        )

        ruleset_data = PersonalDataIndicatorRulesetData(
            name="personal_data_indicator",
            version="1.0.0",
            description="Test ruleset",
            categories=["email", "phone", "name"],
            rules=[rule],
        )

        assert len(ruleset_data.rules) == 1
        assert ruleset_data.rules[0].category == "email"

    def test_ruleset_data_rejects_invalid_category(self) -> None:
        """Test PersonalDataIndicatorRulesetData rejects invalid rule categories."""
        rule = PersonalDataIndicatorRule(
            name="invalid_rule",
            description="Rule with invalid category",
            patterns=("test",),
            category="invalid_category",  # Not in master list
        )

        with pytest.raises(ValidationError, match="invalid category"):
            PersonalDataIndicatorRulesetData(
                name="personal_data_indicator",
                version="1.0.0",
                description="Test ruleset",
                categories=["email", "phone"],  # Does not include 'invalid_category'
                rules=[rule],
            )


# =============================================================================
# Ruleset-specific Tests (unique to PersonalDataIndicatorRuleset)
# =============================================================================


class TestPersonalDataIndicatorRuleset:
    """Test cases for PersonalDataIndicatorRuleset-specific behaviour."""

    @pytest.fixture
    def ruleset(self) -> PersonalDataIndicatorRuleset:
        """Provide a PersonalDataIndicatorRuleset instance for testing."""
        return PersonalDataIndicatorRuleset()

    def test_rules_have_patterns(self, ruleset: PersonalDataIndicatorRuleset) -> None:
        """Test that all rules have patterns defined."""
        rules = ruleset.get_rules()

        for rule in rules:
            assert len(rule.patterns) > 0

    def test_all_rules_have_valid_categories(
        self, ruleset: PersonalDataIndicatorRuleset
    ) -> None:
        """Test that all rules have category field populated."""
        rules = ruleset.get_rules()

        for rule in rules:
            assert rule.category, f"Rule '{rule.name}' has empty category"

    def test_ruleset_is_framework_agnostic(
        self, ruleset: PersonalDataIndicatorRuleset
    ) -> None:
        """Test that ruleset does not contain GDPR-specific metadata."""
        # The ruleset data should not have special_category_types
        # This is verified by the Pydantic model not having that field
        rules = ruleset.get_rules()

        for rule in rules:
            # No rule should have special_category attribute
            assert not hasattr(rule, "special_category")
