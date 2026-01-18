"""Tests for service integrations ruleset."""

import pytest
from pydantic import ValidationError

from waivern_rulesets import AbstractRuleset
from waivern_rulesets.service_integrations import (
    ServiceIntegrationRule,
    ServiceIntegrationsRuleset,
    ServiceIntegrationsRulesetData,
)
from waivern_rulesets.testing import RulesetContractTests

# =============================================================================
# Contract Tests (inherited from RulesetContractTests)
# =============================================================================


class TestServiceIntegrationsRulesetContract(
    RulesetContractTests[ServiceIntegrationRule]
):
    """Contract tests for ServiceIntegrationsRuleset.

    Inherits all standard ruleset contract tests automatically.

    """

    @pytest.fixture
    def ruleset_class(self) -> type[AbstractRuleset[ServiceIntegrationRule]]:
        """Provide the ruleset class to test."""
        return ServiceIntegrationsRuleset

    @pytest.fixture
    def rule_class(self) -> type[ServiceIntegrationRule]:
        """Provide the rule class used by the ruleset."""
        return ServiceIntegrationRule

    @pytest.fixture
    def expected_name(self) -> str:
        """Provide the expected canonical name of the ruleset."""
        return "service_integrations"


# =============================================================================
# Rule-specific Tests (unique to ServiceIntegrationRule)
# =============================================================================


class TestServiceIntegrationRule:
    """Test cases for the ServiceIntegrationRule class."""

    def test_service_integration_rule_with_all_fields(self) -> None:
        """Test ServiceIntegrationRule with all fields."""
        rule = ServiceIntegrationRule(
            name="aws_integration",
            description="AWS integration rule",
            patterns=("aws", "s3.amazonaws"),
            service_category="cloud_infrastructure",
            purpose_category="OPERATIONAL",
        )

        assert rule.name == "aws_integration"
        assert rule.service_category == "cloud_infrastructure"
        assert rule.purpose_category == "OPERATIONAL"


# =============================================================================
# RulesetData Validation Tests
# =============================================================================


class TestServiceIntegrationsRulesetData:
    """Test cases for the ServiceIntegrationsRulesetData class."""

    def test_ruleset_data_with_valid_categories(self) -> None:
        """Test ServiceIntegrationsRulesetData with valid categories passes validation."""
        rule = ServiceIntegrationRule(
            name="aws_rule",
            description="AWS integration",
            patterns=("aws", "s3"),
            service_category="cloud_infrastructure",
            purpose_category="OPERATIONAL",
        )

        ruleset_data = ServiceIntegrationsRulesetData(
            name="service_integrations",
            version="1.0.0",
            description="Test ruleset",
            service_categories=["cloud_infrastructure", "payment_processing"],
            purpose_categories=["OPERATIONAL", "ANALYTICS"],
            rules=[rule],
        )

        assert len(ruleset_data.rules) == 1
        assert ruleset_data.rules[0].service_category == "cloud_infrastructure"

    def test_ruleset_data_rejects_invalid_service_category(self) -> None:
        """Test ServiceIntegrationsRulesetData rejects invalid service_category."""
        rule = ServiceIntegrationRule(
            name="invalid_rule",
            description="Rule with invalid service_category",
            patterns=("test",),
            service_category="invalid_service",  # Not in master list
            purpose_category="OPERATIONAL",
        )

        with pytest.raises(ValidationError, match="invalid service_category"):
            ServiceIntegrationsRulesetData(
                name="service_integrations",
                version="1.0.0",
                description="Test ruleset",
                service_categories=["cloud_infrastructure", "payment_processing"],
                purpose_categories=["OPERATIONAL", "ANALYTICS"],
                rules=[rule],
            )

    def test_ruleset_data_rejects_invalid_purpose_category(self) -> None:
        """Test ServiceIntegrationsRulesetData rejects invalid purpose_category."""
        rule = ServiceIntegrationRule(
            name="invalid_rule",
            description="Rule with invalid purpose_category",
            patterns=("test",),
            service_category="cloud_infrastructure",
            purpose_category="INVALID_PURPOSE",  # Not in master list
        )

        with pytest.raises(ValidationError, match="invalid purpose_category"):
            ServiceIntegrationsRulesetData(
                name="service_integrations",
                version="1.0.0",
                description="Test ruleset",
                service_categories=["cloud_infrastructure", "payment_processing"],
                purpose_categories=["OPERATIONAL", "ANALYTICS"],
                rules=[rule],
            )


# =============================================================================
# Ruleset-specific Tests
# =============================================================================


class TestServiceIntegrationsRuleset:
    """Test cases for ServiceIntegrationsRuleset-specific behaviour."""

    @pytest.fixture
    def ruleset(self) -> ServiceIntegrationsRuleset:
        """Provide a ServiceIntegrationsRuleset instance for testing."""
        return ServiceIntegrationsRuleset()

    def test_rules_have_service_category_and_purpose_category(
        self, ruleset: ServiceIntegrationsRuleset
    ) -> None:
        """Test that all rules have service_category and purpose_category fields."""
        rules = ruleset.get_rules()

        for rule in rules:
            assert isinstance(rule.service_category, str)
            assert len(rule.service_category) > 0
            assert isinstance(rule.purpose_category, str)
            assert len(rule.purpose_category) > 0
