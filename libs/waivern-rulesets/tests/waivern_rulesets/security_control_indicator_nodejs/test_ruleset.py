"""Unit tests for security control indicator Node.js extension ruleset."""

import pytest

from waivern_rulesets import AbstractRuleset
from waivern_rulesets.security_control_indicator import SecurityControlIndicatorRule
from waivern_rulesets.security_control_indicator_nodejs import (
    SecurityControlIndicatorNodejsRuleset,
)
from waivern_rulesets.testing import RulesetContractTests

# =============================================================================
# Contract Tests (inherited from RulesetContractTests)
# =============================================================================


class TestSecurityControlIndicatorNodejsRulesetContract(
    RulesetContractTests[SecurityControlIndicatorRule]
):
    """Contract tests for SecurityControlIndicatorNodejsRuleset."""

    @pytest.fixture
    def ruleset_class(
        self,
    ) -> type[AbstractRuleset[SecurityControlIndicatorRule]]:
        """Provide the ruleset class to test."""
        return SecurityControlIndicatorNodejsRuleset

    @pytest.fixture
    def rule_class(self) -> type[SecurityControlIndicatorRule]:
        """Provide the rule class used by the ruleset."""
        return SecurityControlIndicatorRule

    @pytest.fixture
    def expected_name(self) -> str:
        """Provide the expected canonical name of the ruleset."""
        return "security_control_indicator_nodejs"


# =============================================================================
# Node.js pattern presence
# =============================================================================


class TestSecurityControlIndicatorNodejsPatterns:
    """Verify the Node.js ruleset contains the expected Express/Node.js-specific patterns."""

    def test_nodejs_patterns_are_present_in_nodejs_ruleset(self) -> None:
        """Verify all Node.js/Express-specific patterns are present in the ruleset."""
        ruleset = SecurityControlIndicatorNodejsRuleset()
        all_patterns = {p for rule in ruleset.get_rules() for p in rule.patterns}
        expected_nodejs_patterns = {
            "jwt.verify",
            "jwtVerify",
            "helmet",
            "rateLimit",
            "rateLimiting",
            "escapeHtml",
            "sanitizeInput",
            "sanitizeHtml",
            "child_process",
            "execSync",
            "spawnSync",
        }
        assert expected_nodejs_patterns <= all_patterns
