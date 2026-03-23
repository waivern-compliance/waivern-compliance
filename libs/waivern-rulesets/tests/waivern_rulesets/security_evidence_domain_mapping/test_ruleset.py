"""Unit tests for security evidence domain mapping ruleset."""

import pytest
from pydantic import ValidationError
from waivern_schemas.security_domain import SecurityDomain

from waivern_rulesets import AbstractRuleset
from waivern_rulesets.crypto_quality_indicator import CryptoQualityIndicatorRuleset
from waivern_rulesets.data_collection import DataCollectionRuleset
from waivern_rulesets.personal_data_indicator import PersonalDataIndicatorRuleset
from waivern_rulesets.processing_purposes import ProcessingPurposesRuleset
from waivern_rulesets.security_evidence_domain_mapping import (
    SecurityEvidenceDomainMappingRule,
    SecurityEvidenceDomainMappingRuleset,
    SecurityEvidenceDomainMappingRulesetData,
)
from waivern_rulesets.service_integrations import ServiceIntegrationsRuleset
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
    """Test validators on the security evidence domain mapping ruleset models.

    security_domain and secondary_domain are validated by Pydantic as SecurityDomain
    enum fields on SecurityEvidenceDomainMappingRule. indicator_values are still
    validated by a cross-field model_validator on the data class against the upstream
    master lists (purpose_slugs, indicator_categories, algorithm_values).
    """

    def test_rejects_invalid_security_domain(self) -> None:
        """A rule with an unrecognised security_domain string is rejected at construction."""
        with pytest.raises(ValidationError):
            SecurityEvidenceDomainMappingRule(
                name="invalid_domain_rule",
                description="Rule with invalid security_domain",
                source_type="purpose",
                indicator_values=("user_identity_login",),
                security_domain="nonexistent_domain",  # type: ignore[arg-type]
            )

    def test_rejects_invalid_secondary_domain(self) -> None:
        """A rule with an unrecognised secondary_domain string is rejected at construction."""
        with pytest.raises(ValidationError):
            SecurityEvidenceDomainMappingRule(
                name="invalid_secondary_rule",
                description="Rule with invalid secondary_domain",
                source_type="category",
                indicator_values=("email",),
                security_domain=SecurityDomain.DATA_PROTECTION,
                secondary_domain="nonexistent_domain",  # type: ignore[arg-type]
            )

    def test_rejects_invalid_purpose_indicator_values(self) -> None:
        """Test that purpose rules with slugs not in purpose_slugs list are rejected."""
        rule = SecurityEvidenceDomainMappingRule(
            name="invalid_purpose_rule",
            description="Rule with invalid purpose slug",
            source_type="purpose",
            indicator_values=("nonexistent_purpose_slug",),
            security_domain=SecurityDomain.AUTHENTICATION,
        )

        with pytest.raises(ValidationError, match="invalid purpose indicator_values"):
            SecurityEvidenceDomainMappingRulesetData(
                name="test_ruleset",
                version="1.0.0",
                description="Test ruleset",
                purpose_slugs=["user_identity_login"],
                indicator_categories=["email"],
                algorithm_values=["bcrypt"],
                service_category_values=["cloud_infrastructure"],
                collection_type_values=["form_data"],
                rules=[rule],
            )

    def test_rejects_invalid_category_indicator_values(self) -> None:
        """Test that category rules with values not in indicator_categories list are rejected."""
        rule = SecurityEvidenceDomainMappingRule(
            name="invalid_category_rule",
            description="Rule with invalid indicator category",
            source_type="category",
            indicator_values=("nonexistent_category",),
            security_domain=SecurityDomain.DATA_PROTECTION,
        )

        with pytest.raises(ValidationError, match="invalid category indicator_values"):
            SecurityEvidenceDomainMappingRulesetData(
                name="test_ruleset",
                version="1.0.0",
                description="Test ruleset",
                purpose_slugs=["user_identity_login"],
                indicator_categories=["email"],
                algorithm_values=["bcrypt"],
                service_category_values=["cloud_infrastructure"],
                collection_type_values=["form_data"],
                rules=[rule],
            )

    def test_rejects_invalid_algorithm_indicator_values(self) -> None:
        """Test that algorithm rules with values not in algorithm_values list are rejected."""
        rule = SecurityEvidenceDomainMappingRule(
            name="invalid_algorithm_rule",
            description="Rule with invalid algorithm value",
            source_type="algorithm",
            indicator_values=("nonexistent_algo",),
            security_domain=SecurityDomain.ENCRYPTION,
        )

        with pytest.raises(ValidationError, match="invalid algorithm indicator_values"):
            SecurityEvidenceDomainMappingRulesetData(
                name="test_ruleset",
                version="1.0.0",
                description="Test ruleset",
                purpose_slugs=["user_identity_login"],
                indicator_categories=["email"],
                algorithm_values=["bcrypt"],
                service_category_values=["cloud_infrastructure"],
                collection_type_values=["form_data"],
                rules=[rule],
            )

    def test_rejects_invalid_service_category_indicator_values(self) -> None:
        """Test that service_category rules with values not in service_category_values list are rejected."""
        rule = SecurityEvidenceDomainMappingRule(
            name="invalid_service_category_rule",
            description="Rule with invalid service category",
            source_type="service_category",
            indicator_values=("nonexistent_service",),
            security_domain=SecurityDomain.SUPPLIER_MANAGEMENT,
        )

        with pytest.raises(
            ValidationError, match="invalid service_category indicator_values"
        ):
            SecurityEvidenceDomainMappingRulesetData(
                name="test_ruleset",
                version="1.0.0",
                description="Test ruleset",
                purpose_slugs=["user_identity_login"],
                indicator_categories=["email"],
                algorithm_values=["bcrypt"],
                service_category_values=["cloud_infrastructure"],
                collection_type_values=["form_data"],
                rules=[rule],
            )

    def test_rejects_invalid_collection_type_indicator_values(self) -> None:
        """Test that collection_type rules with values not in collection_type_values list are rejected."""
        rule = SecurityEvidenceDomainMappingRule(
            name="invalid_collection_type_rule",
            description="Rule with invalid collection type",
            source_type="collection_type",
            indicator_values=("nonexistent_collection",),
            security_domain=SecurityDomain.DATA_PROTECTION,
        )

        with pytest.raises(
            ValidationError, match="invalid collection_type indicator_values"
        ):
            SecurityEvidenceDomainMappingRulesetData(
                name="test_ruleset",
                version="1.0.0",
                description="Test ruleset",
                purpose_slugs=["user_identity_login"],
                indicator_categories=["email"],
                algorithm_values=["bcrypt"],
                service_category_values=["cloud_infrastructure"],
                collection_type_values=["form_data"],
                rules=[rule],
            )

    def test_accepts_valid_rule_with_secondary_domain(self) -> None:
        """Test that a valid rule with optional secondary_domain is accepted."""
        rule = SecurityEvidenceDomainMappingRule(
            name="valid_rule_with_secondary",
            description="Valid rule with secondary domain",
            source_type="category",
            indicator_values=("health",),
            security_domain=SecurityDomain.DATA_PROTECTION,
            secondary_domain=SecurityDomain.PEOPLE_CONTROLS,
        )

        # Should not raise
        SecurityEvidenceDomainMappingRulesetData(
            name="test_ruleset",
            version="1.0.0",
            description="Test ruleset",
            purpose_slugs=["user_identity_login"],
            indicator_categories=["health"],
            algorithm_values=["bcrypt"],
            service_category_values=["cloud_infrastructure"],
            collection_type_values=["form_data"],
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

    def test_all_algorithm_values_are_covered(
        self, ruleset: SecurityEvidenceDomainMappingRuleset
    ) -> None:
        """Test that every algorithm from the crypto_quality_indicator ruleset is mapped."""
        all_algorithms: set[str] = {
            rule.algorithm for rule in CryptoQualityIndicatorRuleset().get_rules()
        }

        mapped_algorithms: set[str] = {
            v
            for rule in ruleset.get_rules()
            if rule.source_type == "algorithm"
            for v in rule.indicator_values
        }

        uncovered = all_algorithms - mapped_algorithms
        assert not uncovered, f"Algorithm values not covered by any rule: {uncovered}"

    def test_algorithm_rules_use_valid_algorithm_values(
        self, ruleset: SecurityEvidenceDomainMappingRuleset
    ) -> None:
        """Test that all algorithm indicator_values are valid algorithms from the upstream ruleset."""
        valid_algorithms: set[str] = {
            rule.algorithm for rule in CryptoQualityIndicatorRuleset().get_rules()
        }

        for rule in ruleset.get_rules():
            if rule.source_type == "algorithm":
                invalid = [
                    v for v in rule.indicator_values if v not in valid_algorithms
                ]
                assert not invalid, (
                    f"Rule '{rule.name}' has invalid algorithm values: {invalid}"
                )

    def test_all_service_categories_are_covered(
        self, ruleset: SecurityEvidenceDomainMappingRuleset
    ) -> None:
        """Test that every service_category from the service_integrations ruleset is mapped."""
        all_service_categories: set[str] = {
            rule.service_category for rule in ServiceIntegrationsRuleset().get_rules()
        }

        mapped_categories: set[str] = {
            v
            for rule in ruleset.get_rules()
            if rule.source_type == "service_category"
            for v in rule.indicator_values
        }

        uncovered = all_service_categories - mapped_categories
        assert not uncovered, f"Service categories not covered by any rule: {uncovered}"

    def test_all_collection_types_are_covered(
        self, ruleset: SecurityEvidenceDomainMappingRuleset
    ) -> None:
        """Test that every collection_type from the data_collection ruleset is mapped."""
        all_collection_types: set[str] = {
            rule.collection_type for rule in DataCollectionRuleset().get_rules()
        }

        mapped_types: set[str] = {
            v
            for rule in ruleset.get_rules()
            if rule.source_type == "collection_type"
            for v in rule.indicator_values
        }

        uncovered = all_collection_types - mapped_types
        assert not uncovered, f"Collection types not covered by any rule: {uncovered}"

    def test_service_category_rules_use_valid_service_categories(
        self, ruleset: SecurityEvidenceDomainMappingRuleset
    ) -> None:
        """Test that all service_category indicator_values are valid from the upstream ruleset."""
        valid_categories: set[str] = {
            rule.service_category for rule in ServiceIntegrationsRuleset().get_rules()
        }

        for rule in ruleset.get_rules():
            if rule.source_type == "service_category":
                invalid = [
                    v for v in rule.indicator_values if v not in valid_categories
                ]
                assert not invalid, (
                    f"Rule '{rule.name}' has invalid service categories: {invalid}"
                )

    def test_collection_type_rules_use_valid_collection_types(
        self, ruleset: SecurityEvidenceDomainMappingRuleset
    ) -> None:
        """Test that all collection_type indicator_values are valid from the upstream ruleset."""
        valid_types: set[str] = {
            rule.collection_type for rule in DataCollectionRuleset().get_rules()
        }

        for rule in ruleset.get_rules():
            if rule.source_type == "collection_type":
                invalid = [v for v in rule.indicator_values if v not in valid_types]
                assert not invalid, (
                    f"Rule '{rule.name}' has invalid collection types: {invalid}"
                )

    def test_third_party_identity_rule_has_authentication_secondary_domain(
        self, ruleset: SecurityEvidenceDomainMappingRuleset
    ) -> None:
        """Test that identity_management maps to supplier_management + authentication secondary."""
        rules = ruleset.get_rules()

        identity_rule = next(
            (r for r in rules if r.name == "third_party_identity"), None
        )
        assert identity_rule is not None, (
            "Expected 'third_party_identity' rule in ruleset"
        )
        assert identity_rule.security_domain == "supplier_management"
        assert identity_rule.secondary_domain == "authentication"
