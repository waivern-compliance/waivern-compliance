"""Unit tests for personal data indicator ERP extension ruleset."""

import pytest

from waivern_rulesets import AbstractRuleset
from waivern_rulesets.personal_data_indicator import PersonalDataIndicatorRule
from waivern_rulesets.personal_data_indicator_erp import PersonalDataIndicatorERPRuleset
from waivern_rulesets.testing import RulesetContractTests

# =============================================================================
# Contract Tests (inherited from RulesetContractTests)
# =============================================================================


class TestPersonalDataIndicatorERPRulesetContract(
    RulesetContractTests[PersonalDataIndicatorRule]
):
    """Contract tests for PersonalDataIndicatorERPRuleset."""

    @pytest.fixture
    def ruleset_class(self) -> type[AbstractRuleset[PersonalDataIndicatorRule]]:
        """Provide the ruleset class to test."""
        return PersonalDataIndicatorERPRuleset

    @pytest.fixture
    def rule_class(self) -> type[PersonalDataIndicatorRule]:
        """Provide the rule class used by the ruleset."""
        return PersonalDataIndicatorRule

    @pytest.fixture
    def expected_name(self) -> str:
        """Provide the expected canonical name of the ruleset."""
        return "personal_data_indicator_erp"


# =============================================================================
# ERP pattern presence
# =============================================================================


class TestPersonalDataIndicatorERPPatterns:
    """Verify that the ERP ruleset contains the expected Dolibarr-specific patterns."""

    def test_erp_patterns_are_present_in_erp_ruleset(self) -> None:
        """Verify all Dolibarr-specific patterns are present in the ERP ruleset."""
        ruleset = PersonalDataIndicatorERPRuleset()
        all_patterns = {p for rule in ruleset.get_rules() for p in rule.patterns}

        assert {"fk_user", "socid"} <= all_patterns
