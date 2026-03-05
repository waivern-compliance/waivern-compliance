"""Unit tests for security domains vocabulary ruleset."""

import pytest
from pydantic import ValidationError
from waivern_core import SecurityDomain

from waivern_rulesets import AbstractRuleset
from waivern_rulesets.security_domains import (
    SecurityDomainRule,
    SecurityDomainsRuleset,
)
from waivern_rulesets.testing import RulesetContractTests

# =============================================================================
# Contract Tests (inherited from RulesetContractTests)
# =============================================================================


class TestSecurityDomainsRulesetContract(RulesetContractTests[SecurityDomainRule]):
    """Contract tests for SecurityDomainsRuleset."""

    @pytest.fixture
    def ruleset_class(self) -> type[AbstractRuleset[SecurityDomainRule]]:
        """Provide the ruleset class to test."""
        return SecurityDomainsRuleset

    @pytest.fixture
    def rule_class(self) -> type[SecurityDomainRule]:
        """Provide the rule class used by the ruleset."""
        return SecurityDomainRule

    @pytest.fixture
    def expected_name(self) -> str:
        """Provide the expected canonical name of the ruleset."""
        return "security_domains"


# =============================================================================
# Model Validator Tests
# =============================================================================


class TestSecurityDomainRuleValidation:
    """Test validation on the security domain rule model."""

    def test_rejects_invalid_security_domain(self) -> None:
        """A rule with an unrecognised security_domain string is rejected at construction."""
        with pytest.raises(ValidationError):
            SecurityDomainRule(
                name="invalid_domain",
                description="Rule with invalid security_domain",
                security_domain="not_a_real_domain",  # type: ignore[arg-type]
            )


# =============================================================================
# Business Rule Tests (actual YAML data)
# =============================================================================


class TestSecurityDomainsRulesetBusinessRules:
    """Test business rules in the actual YAML ruleset data."""

    @pytest.fixture
    def ruleset(self) -> SecurityDomainsRuleset:
        """Provide loaded ruleset instance."""
        return SecurityDomainsRuleset()

    def test_all_security_domain_enum_values_present(
        self, ruleset: SecurityDomainsRuleset
    ) -> None:
        """Ruleset domains exactly match SecurityDomain enum — no gaps, no extras.

        Uses SecurityDomain from waivern_core as the authoritative source — no
        hardcoded domain list to keep in sync. Adding a new value to the enum
        without a corresponding YAML rule will fail this test.
        """
        ruleset_domains = {rule.security_domain for rule in ruleset.get_rules()}
        assert ruleset_domains == set(SecurityDomain), (
            f"Mismatch between ruleset and SecurityDomain enum.\n"
            f"  Missing from ruleset: {set(SecurityDomain) - ruleset_domains}\n"
            f"  Extra in ruleset:     {ruleset_domains - set(SecurityDomain)}"
        )
