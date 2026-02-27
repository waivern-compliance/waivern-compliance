"""Unit tests for security evidence domain mapping ruleset."""

import pytest
from pydantic import ValidationError

from waivern_rulesets import AbstractRuleset
from waivern_rulesets.personal_data_indicator import PersonalDataIndicatorRuleset
from waivern_rulesets.processing_purposes import ProcessingPurposesRuleset
from waivern_rulesets.security_evidence_domain_mapping import (
    SecurityEvidenceDomainMappingRule,
    SecurityEvidenceDomainMappingRuleset,
    SecurityEvidenceDomainMappingRulesetData,
)
from waivern_rulesets.testing import RulesetContractTests

# =============================================================================
# Contract Tests (inherited from RulesetContractTests)
# =============================================================================


class TestSecurityEvidenceDomainMappingRulesetContract(
    RulesetContractTests[SecurityEvidenceDomainMappingRule]
):
    """Contract tests for SecurityEvidenceDomainMappingRuleset."""

    @pytest.fixture
    def ruleset_class(
        self,
    ) -> type[AbstractRuleset[SecurityEvidenceDomainMappingRule]]:
        """Provide the ruleset class to test."""
        return SecurityEvidenceDomainMappingRuleset

    @pytest.fixture
    def rule_class(self) -> type[SecurityEvidenceDomainMappingRule]:
        """Provide the rule class used by the ruleset."""
        return SecurityEvidenceDomainMappingRule

    @pytest.fixture
    def expected_name(self) -> str:
        """Provide the expected canonical name of the ruleset."""
        return "security_evidence_domain_mapping"


# =============================================================================
# Model Validator Tests (our custom validation logic)
# =============================================================================


class TestSecurityEvidenceDomainMappingRulesetDataValidation:
    """Test our custom model validators on the ruleset data class.

    The mapping ruleset validates three cross-field constraints:
    - security_domain must be in the master security_domains list
    - secondary_domain (if set) must be in the master security_domains list
    - indicator_values must match the appropriate master list based on source_type
    """

    def test_rejects_invalid_security_domain(self) -> None:
        """Test that rules with security_domain not in master list are rejected."""
        rule = SecurityEvidenceDomainMappingRule(
            name="invalid_domain_rule",
            description="Rule with invalid security_domain",
            source_type="purpose",
            indicator_values=("user_identity_login",),
            security_domain="nonexistent_domain",
        )

        with pytest.raises(ValidationError, match="invalid security_domain"):
            SecurityEvidenceDomainMappingRulesetData(
                name="test_ruleset",
                version="1.0.0",
                description="Test ruleset",
                security_domains=["authentication", "data_protection"],
                purpose_slugs=["user_identity_login"],
                indicator_categories=["email"],
                rules=[rule],
            )

    def test_rejects_invalid_secondary_domain(self) -> None:
        """Test that rules with secondary_domain not in master list are rejected."""
        rule = SecurityEvidenceDomainMappingRule(
            name="invalid_secondary_rule",
            description="Rule with invalid secondary_domain",
            source_type="category",
            indicator_values=("email",),
            security_domain="data_protection",
            secondary_domain="nonexistent_domain",
        )

        with pytest.raises(ValidationError, match="invalid secondary_domain"):
            SecurityEvidenceDomainMappingRulesetData(
                name="test_ruleset",
                version="1.0.0",
                description="Test ruleset",
                security_domains=["authentication", "data_protection"],
                purpose_slugs=["user_identity_login"],
                indicator_categories=["email"],
                rules=[rule],
            )

    def test_rejects_invalid_purpose_indicator_values(self) -> None:
        """Test that purpose rules with slugs not in purpose_slugs list are rejected."""
        rule = SecurityEvidenceDomainMappingRule(
            name="invalid_purpose_rule",
            description="Rule with invalid purpose slug",
            source_type="purpose",
            indicator_values=("nonexistent_purpose_slug",),
            security_domain="authentication",
        )

        with pytest.raises(ValidationError, match="invalid purpose indicator_values"):
            SecurityEvidenceDomainMappingRulesetData(
                name="test_ruleset",
                version="1.0.0",
                description="Test ruleset",
                security_domains=["authentication"],
                purpose_slugs=["user_identity_login"],
                indicator_categories=["email"],
                rules=[rule],
            )

    def test_rejects_invalid_category_indicator_values(self) -> None:
        """Test that category rules with values not in indicator_categories list are rejected."""
        rule = SecurityEvidenceDomainMappingRule(
            name="invalid_category_rule",
            description="Rule with invalid indicator category",
            source_type="category",
            indicator_values=("nonexistent_category",),
            security_domain="data_protection",
        )

        with pytest.raises(ValidationError, match="invalid category indicator_values"):
            SecurityEvidenceDomainMappingRulesetData(
                name="test_ruleset",
                version="1.0.0",
                description="Test ruleset",
                security_domains=["data_protection"],
                purpose_slugs=["user_identity_login"],
                indicator_categories=["email"],
                rules=[rule],
            )

    def test_accepts_valid_rule_with_secondary_domain(self) -> None:
        """Test that a valid rule with optional secondary_domain is accepted."""
        rule = SecurityEvidenceDomainMappingRule(
            name="valid_rule_with_secondary",
            description="Valid rule with secondary domain",
            source_type="category",
            indicator_values=("health",),
            security_domain="data_protection",
            secondary_domain="people_controls",
        )

        # Should not raise
        SecurityEvidenceDomainMappingRulesetData(
            name="test_ruleset",
            version="1.0.0",
            description="Test ruleset",
            security_domains=["data_protection", "people_controls"],
            purpose_slugs=["user_identity_login"],
            indicator_categories=["health"],
            rules=[rule],
        )


# =============================================================================
# Business Rule Tests (actual YAML data)
# =============================================================================


class TestSecurityEvidenceDomainMappingRulesetBusinessRules:
    """Test business rules in the actual YAML ruleset data.

    Business rule assertions use only the public get_rules() API.
    Coverage completeness is verified by cross-referencing the upstream
    rulesets (ProcessingPurposesRuleset, PersonalDataIndicatorRuleset)
    directly, so the tests self-update if those rulesets grow.
    """

    @pytest.fixture
    def ruleset(self) -> SecurityEvidenceDomainMappingRuleset:
        """Provide loaded ruleset instance."""
        return SecurityEvidenceDomainMappingRuleset()

    def test_all_purpose_slugs_are_covered(
        self, ruleset: SecurityEvidenceDomainMappingRuleset
    ) -> None:
        """Test that every purpose slug from the processing_purposes ruleset is mapped."""
        all_purpose_slugs: set[str] = {
            rule.purpose for rule in ProcessingPurposesRuleset().get_rules()
        }

        mapped_purposes: set[str] = {
            v
            for rule in ruleset.get_rules()
            if rule.source_type == "purpose"
            for v in rule.indicator_values
        }

        uncovered = all_purpose_slugs - mapped_purposes
        assert not uncovered, f"Purpose slugs not covered by any rule: {uncovered}"

    def test_all_categories_are_covered(
        self, ruleset: SecurityEvidenceDomainMappingRuleset
    ) -> None:
        """Test that every indicator category from personal_data_indicator ruleset is mapped."""
        all_categories: set[str] = {
            rule.category for rule in PersonalDataIndicatorRuleset().get_rules()
        }

        mapped_categories: set[str] = {
            v
            for rule in ruleset.get_rules()
            if rule.source_type == "category"
            for v in rule.indicator_values
        }

        uncovered = all_categories - mapped_categories
        assert not uncovered, (
            f"Indicator categories not covered by any rule: {uncovered}"
        )

    def test_sensitive_personal_data_rule_has_people_controls_secondary_domain(
        self, ruleset: SecurityEvidenceDomainMappingRuleset
    ) -> None:
        """Test that government_id and Art.9 categories map to people_controls as secondary."""
        rules = ruleset.get_rules()

        sensitive_rule = next(
            (r for r in rules if r.name == "sensitive_personal_data"), None
        )
        assert sensitive_rule is not None, (
            "Expected 'sensitive_personal_data' rule in ruleset"
        )
        assert sensitive_rule.security_domain == "data_protection"
        assert sensitive_rule.secondary_domain == "people_controls"

    def test_purpose_rules_use_valid_purpose_slugs(
        self, ruleset: SecurityEvidenceDomainMappingRuleset
    ) -> None:
        """Test that all purpose indicator_values are valid purpose slugs from the upstream ruleset."""
        valid_slugs: set[str] = {
            rule.purpose for rule in ProcessingPurposesRuleset().get_rules()
        }

        for rule in ruleset.get_rules():
            if rule.source_type == "purpose":
                invalid = [v for v in rule.indicator_values if v not in valid_slugs]
                assert not invalid, (
                    f"Rule '{rule.name}' has invalid purpose slugs: {invalid}"
                )

    def test_category_rules_use_valid_indicator_categories(
        self, ruleset: SecurityEvidenceDomainMappingRuleset
    ) -> None:
        """Test that all category indicator_values are valid categories from the upstream ruleset."""
        valid_categories: set[str] = {
            rule.category for rule in PersonalDataIndicatorRuleset().get_rules()
        }

        for rule in ruleset.get_rules():
            if rule.source_type == "category":
                invalid = [
                    v for v in rule.indicator_values if v not in valid_categories
                ]
                assert not invalid, (
                    f"Rule '{rule.name}' has invalid indicator categories: {invalid}"
                )
