"""Unit tests for ISO 27001 domains ruleset."""

import pytest
from pydantic import ValidationError
from waivern_core import SecurityDomain

from waivern_rulesets import AbstractRuleset
from waivern_rulesets.iso27001_domains import (
    ISO27001DomainsRule,
    ISO27001DomainsRuleset,
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
    """Test validation on the ISO 27001 domains ruleset models.

    security_domains on ISO27001DomainsRule is validated by Pydantic as a
    tuple[SecurityDomain, ...] field — rejection happens at rule construction.
    """

    def _make_valid_rule(self, name: str = "test_rule") -> ISO27001DomainsRule:
        """Build a minimal valid rule for use in validator tests."""
        return ISO27001DomainsRule(
            name=name,
            description="A test rule",
            control_ref="A.5.1",
            security_domains=(SecurityDomain.AUTHENTICATION,),
            evidence_source=("TECHNICAL",),
            attestation_required=False,
            control_type="preventive",
            cia=("confidentiality",),
            cybersecurity_concept="identify",
            operational_capability="governance",
            iso_security_domain="governance_and_ecosystem",
            guidance_text="A.5.1 Policies for information security.",
        )

    def test_rejects_invalid_security_domain(self) -> None:
        """A rule with an unrecognised security_domains value is rejected at construction."""
        with pytest.raises(ValidationError):
            ISO27001DomainsRule(
                name="invalid_domain_rule",
                description="Rule with invalid security_domain",
                control_ref="A.5.1",
                security_domains=("nonexistent_domain",),  # type: ignore[arg-type]
                evidence_source=(),
                attestation_required=True,
                control_type="preventive",
                cia=("confidentiality",),
                cybersecurity_concept="identify",
                operational_capability="governance",
                iso_security_domain="governance_and_ecosystem",
                guidance_text="Some guidance.",
            )

    def test_rejects_rule_with_empty_guidance_text(self) -> None:
        """Test that rules with empty guidance_text are rejected."""
        with pytest.raises(ValidationError):
            ISO27001DomainsRule(
                name="empty_guidance_rule",
                description="Rule with empty guidance_text",
                control_ref="A.5.1",
                security_domains=(),
                evidence_source=(),
                attestation_required=True,
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
        """Test that all four Annex A clauses have at least one control (A.5, A.6, A.7, A.8)."""
        clauses = {rule.control_ref[:3] for rule in ruleset.get_rules()}
        assert {"A.5", "A.6", "A.7", "A.8"}.issubset(clauses), (
            f"Missing Annex A clauses. Found clause prefixes: {clauses}"
        )

    def test_control_ref_values_are_unique(
        self, ruleset: ISO27001DomainsRuleset
    ) -> None:
        """Test that no two rules share the same control_ref value."""
        refs = [rule.control_ref for rule in ruleset.get_rules()]
        assert len(refs) == len(set(refs)), (
            f"Duplicate control_ref values: {[r for r in refs if refs.count(r) > 1]}"
        )

    def test_all_security_domains_are_covered(
        self, ruleset: ISO27001DomainsRuleset
    ) -> None:
        """Test that every SecurityDomain value is covered by at least one rule.

        Ensures no security_evidence items are silently unassessable because their
        domain maps to no ISO 27001 control. Physical controls cover physical_security
        via document evidence from physical security policies and audit reports.

        Uses SecurityDomain from waivern_core as the authoritative source — no
        hardcoded set to keep in sync.
        """
        expected_domains = {d.value for d in SecurityDomain}
        covered_domains = {
            d for rule in ruleset.get_rules() for d in rule.security_domains
        }
        uncovered = expected_domains - covered_domains

        assert not uncovered, f"Security domains not covered by any rule: {uncovered}"

    def test_all_93_controls_are_present(self, ruleset: ISO27001DomainsRuleset) -> None:
        """Test that exactly 93 individual Annex A controls are defined in the ruleset."""
        assert len(ruleset.get_rules()) == 93, (
            f"Expected 93 Annex A controls, got {len(ruleset.get_rules())}"
        )

    def test_physical_controls_have_physical_security_domain(
        self, ruleset: ISO27001DomainsRuleset
    ) -> None:
        """Test that all A.7 physical controls include physical_security in their security_domains.

        Document evidence from physical security policies and audit reports carries
        security_domain: physical_security and must be routable to A.7.x controls.
        """
        physical_rules = [
            r for r in ruleset.get_rules() if r.control_ref.startswith("A.7.")
        ]
        violations = [
            r.control_ref
            for r in physical_rules
            if "physical_security" not in r.security_domains
        ]
        assert not violations, (
            f"A.7 controls missing physical_security domain: {violations}"
        )

    def test_physical_controls_require_attestation(
        self, ruleset: ISO27001DomainsRuleset
    ) -> None:
        """Test that all A.7 physical controls have attestation_required=True.

        Physical controls (perimeters, entry, equipment) cannot be verified from
        documents alone — a physical site visit is always required.
        """
        physical_rules = [
            r for r in ruleset.get_rules() if r.control_ref.startswith("A.7.")
        ]
        violations = [
            r.control_ref for r in physical_rules if not r.attestation_required
        ]
        assert not violations, (
            f"A.7 controls missing attestation_required=True: {violations}"
        )
