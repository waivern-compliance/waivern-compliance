"""Unit tests for security control indicator ruleset."""

import pytest
from pydantic import ValidationError

from waivern_rulesets import AbstractRuleset
from waivern_rulesets.security_control_indicator import (
    SecurityControlIndicatorRule,
    SecurityControlIndicatorRuleset,
    SecurityControlIndicatorRulesetData,
)
from waivern_rulesets.testing import RulesetContractTests

# =============================================================================
# Contract Tests (inherited from RulesetContractTests)
# =============================================================================


class TestSecurityControlIndicatorRulesetContract(
    RulesetContractTests[SecurityControlIndicatorRule]
):
    """Contract tests for SecurityControlIndicatorRuleset."""

    @pytest.fixture
    def ruleset_class(
        self,
    ) -> type[AbstractRuleset[SecurityControlIndicatorRule]]:
        """Provide the ruleset class to test."""
        return SecurityControlIndicatorRuleset

    @pytest.fixture
    def rule_class(self) -> type[SecurityControlIndicatorRule]:
        """Provide the rule class used by the ruleset."""
        return SecurityControlIndicatorRule

    @pytest.fixture
    def expected_name(self) -> str:
        """Provide the expected canonical name of the ruleset."""
        return "security_control_indicator"


# =============================================================================
# Model Validator Tests
# =============================================================================


class TestSecurityControlIndicatorRulesetDataValidation:
    """Test the custom model validator on the ruleset data class.

    The security_control_indicator ruleset validates one cross-field constraint:
    - security_domain must be in the security_domains master list.
    """

    def test_rejects_security_domain_not_in_master_list(self) -> None:
        """A rule whose security_domain is absent from the master list is rejected."""
        rule = SecurityControlIndicatorRule(
            name="invalid_domain_rule",
            description="Rule with invalid security_domain",
            security_domain="nonexistent_domain",
            polarity="positive",
            patterns=("prepared_statement",),
        )

        with pytest.raises(ValidationError, match="invalid security_domain"):
            SecurityControlIndicatorRulesetData(
                name="test_ruleset",
                version="1.0.0",
                description="Test ruleset",
                security_domains=["authentication", "vulnerability_management"],
                rules=[rule],
            )


# =============================================================================
# Business Rule Tests (actual YAML data)
# =============================================================================


class TestSecurityControlIndicatorRulesetBusinessRules:
    """Test business rules in the actual YAML ruleset data.

    Business rule assertions use only the public get_rules() API.
    """

    @pytest.fixture
    def ruleset(self) -> SecurityControlIndicatorRuleset:
        """Provide loaded ruleset instance."""
        return SecurityControlIndicatorRuleset()

    def test_all_six_initial_domains_are_covered(
        self, ruleset: SecurityControlIndicatorRuleset
    ) -> None:
        """Each of the six initial security domains has at least one rule."""
        expected_domains = {
            "authentication",
            "access_control",
            "logging_monitoring",
            "vulnerability_management",
            "data_protection",
            "network_security",
        }
        covered = {rule.security_domain for rule in ruleset.get_rules()}
        missing = expected_domains - covered
        assert not missing, f"Security domains with no rules: {missing}"

    def test_positive_and_negative_rules_both_present(
        self, ruleset: SecurityControlIndicatorRuleset
    ) -> None:
        """The ruleset contains both positive and negative polarity rules."""
        polarities = {rule.polarity for rule in ruleset.get_rules()}
        assert "positive" in polarities, "Expected at least one positive-polarity rule"
        assert "negative" in polarities, "Expected at least one negative-polarity rule"
