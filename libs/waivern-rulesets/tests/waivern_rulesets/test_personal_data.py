"""Unit tests for PersonalDataRuleset class."""

import pytest

from waivern_rulesets.base import AbstractRuleset
from waivern_rulesets.personal_data import (
    PersonalDataRule,
    PersonalDataRuleset,
)
from waivern_rulesets.testing import RulesetContractTests

# =============================================================================
# Contract Tests (inherited from RulesetContractTests)
# =============================================================================


class TestPersonalDataRulesetContract(RulesetContractTests[PersonalDataRule]):
    """Contract tests for PersonalDataRuleset.

    Inherits all standard ruleset contract tests automatically.

    """

    @pytest.fixture
    def ruleset_class(self) -> type[AbstractRuleset[PersonalDataRule]]:
        """Provide the ruleset class to test."""
        return PersonalDataRuleset

    @pytest.fixture
    def rule_class(self) -> type[PersonalDataRule]:
        """Provide the rule class used by the ruleset."""
        return PersonalDataRule

    @pytest.fixture
    def expected_name(self) -> str:
        """Provide the expected canonical name of the ruleset."""
        return "personal_data"


# =============================================================================
# Rule-specific Tests (unique to PersonalDataRule)
# =============================================================================


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
        )

        assert rule.name == "email_rule"
        assert rule.special_category is False

    def test_personal_data_rule_special_category_default(self) -> None:
        """Test PersonalDataRule special_category defaults to False."""
        rule = PersonalDataRule(
            name="basic_rule",
            description="Basic rule",
            patterns=("test",),
            data_type="basic_profile",
        )

        assert rule.special_category is False


# =============================================================================
# Ruleset-specific Tests (unique to PersonalDataRuleset)
# =============================================================================


class TestPersonalDataRuleset:
    """Test cases for PersonalDataRuleset-specific behaviour."""

    def setup_method(self) -> None:
        """Set up test fixtures for each test method."""
        self.ruleset = PersonalDataRuleset()

    def test_rules_have_patterns(self) -> None:
        """Test that all rules have patterns defined."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert len(rule.patterns) > 0
