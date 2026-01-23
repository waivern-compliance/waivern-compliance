"""Unit tests for personal data indicator ruleset."""

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
    """Contract tests for PersonalDataIndicatorRuleset."""

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
# Model Validator Tests (our custom validation logic)
# =============================================================================


class TestPersonalDataIndicatorRulesetDataValidation:
    """Test our custom model validators on the ruleset data class."""

    def test_rejects_invalid_category(self) -> None:
        """Test that rules with category not in master list are rejected."""
        rule = PersonalDataIndicatorRule(
            name="invalid_rule",
            description="Rule with invalid category",
            patterns=("test",),
            category="invalid_category",
        )

        with pytest.raises(ValidationError, match="invalid category"):
            PersonalDataIndicatorRulesetData(
                name="personal_data_indicator",
                version="1.0.0",
                description="Test ruleset",
                categories=["email", "phone"],
                rules=[rule],
            )
