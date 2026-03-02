"""Unit tests for ISO 27001 domains ruleset."""

import pytest
from pydantic import ValidationError

from waivern_rulesets import AbstractRuleset
from waivern_rulesets.iso27001_domains import (
    ISO27001DomainsRule,
    ISO27001DomainsRuleset,
    ISO27001DomainsRulesetData,  # used in model validator tests
)
from waivern_rulesets.testing import RulesetContractTests

# =============================================================================
# Contract Tests (inherited from RulesetContractTests)
# =============================================================================


class TestISO27001DomainsRulesetContract(RulesetContractTests[ISO27001DomainsRule]):
    """Contract tests for ISO27001DomainsRuleset."""

    @pytest.fixture
    def ruleset_class(self) -> type[AbstractRuleset[ISO27001DomainsRule]]:
        """Provide the ruleset class to test."""
        return ISO27001DomainsRuleset

    @pytest.fixture
    def rule_class(self) -> type[ISO27001DomainsRule]:
        """Provide the rule class used by the ruleset."""
        return ISO27001DomainsRule

    @pytest.fixture
    def expected_name(self) -> str:
        """Provide the expected canonical name of the ruleset."""
        return "iso27001_domains"


# =============================================================================
# Model Validator Tests
# =============================================================================


class TestISO27001DomainsRulesetDataValidation:
    """Test custom model validators on the ruleset data class.

    The iso27001_domains ruleset validates one cross-field constraint:
    - security_domains values in each rule must be in the security_domains master list.
    """

    def _make_valid_rule(self, name: str = "test_rule") -> ISO27001DomainsRule:
        """Build a minimal valid rule for use in validator tests."""
        return ISO27001DomainsRule(
            name=name,
            description="A test rule",
            domain="A.5",
            security_domains=("authentication",),
            control_type="preventive",
            cia=("confidentiality",),
            cybersecurity_concept="identify",
            operational_capability="governance",
            iso_security_domain="governance_and_ecosystem",
            guidance_text="A.5.1 Policies for information security.",
        )

    def test_rejects_invalid_security_domain(self) -> None:
        """Test that rules with a security_domain not in master list are rejected."""
        rule = ISO27001DomainsRule(
            name="invalid_domain_rule",
            description="Rule with invalid security_domain",
            domain="A.5",
            security_domains=("nonexistent_domain",),
            control_type="preventive",
            cia=("confidentiality",),
            cybersecurity_concept="identify",
            operational_capability="governance",
            iso_security_domain="governance_and_ecosystem",
            guidance_text="Some guidance.",
        )

        with pytest.raises(ValidationError, match="invalid security_domains"):
            ISO27001DomainsRulesetData(
                name="test_ruleset",
                version="1.0.0",
                description="Test ruleset",
                security_domains=["authentication"],
                rules=[rule],
            )

    def test_rejects_rule_with_empty_guidance_text(self) -> None:
        """Test that rules with empty guidance_text are rejected."""
        with pytest.raises(ValidationError):
            ISO27001DomainsRule(
                name="empty_guidance_rule",
                description="Rule with empty guidance_text",
                domain="A.5",
                security_domains=("authentication",),
                control_type="preventive",
                cia=("confidentiality",),
                cybersecurity_concept="identify",
                operational_capability="governance",
                iso_security_domain="governance_and_ecosystem",
                guidance_text="",
            )


# =============================================================================
# Business Rule Tests (actual YAML data)
# =============================================================================


class TestISO27001DomainsRulesetBusinessRules:
    """Test business rules in the actual YAML ruleset data.

    Business rule assertions use only the public get_rules() API,
    except for the coverage test which accesses the security_domains master list
    via _load_data() — the designed extension point for extra ruleset data.
    """

    @pytest.fixture
    def ruleset(self) -> ISO27001DomainsRuleset:
        """Provide loaded ruleset instance."""
        return ISO27001DomainsRuleset()

    def test_all_four_annex_a_clauses_present(
        self, ruleset: ISO27001DomainsRuleset
    ) -> None:
        """Test that all four Annex A clauses have a rule (A.5, A.6, A.7, A.8)."""
        domains = {rule.domain for rule in ruleset.get_rules()}
        assert {"A.5", "A.6", "A.7", "A.8"}.issubset(domains), (
            f"Missing Annex A clauses. Found: {domains}"
        )

    def test_domain_values_are_unique(self, ruleset: ISO27001DomainsRuleset) -> None:
        """Test that no two rules share the same domain value."""
        domains = [rule.domain for rule in ruleset.get_rules()]
        assert len(domains) == len(set(domains)), (
            f"Duplicate domain values: {[d for d in domains if domains.count(d) > 1]}"
        )

    def test_every_rule_has_at_least_one_security_domain(
        self, ruleset: ISO27001DomainsRuleset
    ) -> None:
        """Test that no rule has an empty security_domains tuple."""
        for rule in ruleset.get_rules():
            assert len(rule.security_domains) > 0, (
                f"Rule '{rule.name}' (domain {rule.domain}) has no security_domains"
            )

    def test_all_security_domains_are_covered(
        self, ruleset: ISO27001DomainsRuleset
    ) -> None:
        """Test that every security taxonomy domain is covered by at least one rule.

        Ensures no security_evidence items are silently unassessable because their
        domain maps to no Annex A clause.

        DEPENDENCY: Must stay in sync with SecurityDomain enum in waivern-security-evidence.
        When adding or removing a domain there, update this set accordingly.
        """
        expected_domains = {
            "authentication",
            "encryption",
            "access_control",
            "logging_monitoring",
            "vulnerability_management",
            "data_protection",
            "network_security",
            "physical_security",
            "people_controls",
            "supplier_management",
            "incident_management",
            "business_continuity",
        }
        covered_domains = {
            d for rule in ruleset.get_rules() for d in rule.security_domains
        }
        uncovered = expected_domains - covered_domains

        assert not uncovered, f"Security domains not covered by any rule: {uncovered}"
