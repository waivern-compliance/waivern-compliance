"""Unit tests for security control indicator ERP extension ruleset."""

import pytest

from waivern_rulesets import AbstractRuleset
from waivern_rulesets.security_control_indicator import SecurityControlIndicatorRule
from waivern_rulesets.security_control_indicator_erp import (
    SecurityControlIndicatorERPRuleset,
)
from waivern_rulesets.testing import RulesetContractTests

# =============================================================================
# Contract Tests (inherited from RulesetContractTests)
# =============================================================================


class TestSecurityControlIndicatorERPRulesetContract(
    RulesetContractTests[SecurityControlIndicatorRule]
):
    """Contract tests for SecurityControlIndicatorERPRuleset."""

    @pytest.fixture
    def ruleset_class(
        self,
    ) -> type[AbstractRuleset[SecurityControlIndicatorRule]]:
        """Provide the ruleset class to test."""
        return SecurityControlIndicatorERPRuleset

    @pytest.fixture
    def rule_class(self) -> type[SecurityControlIndicatorRule]:
        """Provide the rule class used by the ruleset."""
        return SecurityControlIndicatorRule

    @pytest.fixture
    def expected_name(self) -> str:
        """Provide the expected canonical name of the ruleset."""
        return "security_control_indicator_erp"


# =============================================================================
# ERP pattern presence
# =============================================================================


class TestSecurityControlIndicatorERPPatterns:
    """Verify the ERP ruleset contains the expected Dolibarr-specific patterns."""

    def test_erp_patterns_are_present_in_erp_ruleset(self) -> None:
        """Verify all Dolibarr-specific patterns are present in the ERP ruleset."""
        ruleset = SecurityControlIndicatorERPRuleset()
        all_patterns = {p for rule in ruleset.get_rules() for p in rule.patterns}

        expected_erp_patterns = {
            # access_control
            "hasRight",
            "accessforbidden",
            "restrictedArea",
            "verifCond",
            "checkUserAccess",
            # logging_monitoring
            "addEvent",
            "dol_syslog",
            # vulnerability_management
            "db->escape",
            "db->sanitize",
            "db->idate",
            # authentication
            "hash_hmac",
            "hash_equals",
        }
        assert expected_erp_patterns <= all_patterns
