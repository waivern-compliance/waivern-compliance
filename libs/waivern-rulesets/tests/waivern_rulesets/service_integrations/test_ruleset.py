"""Unit tests for service integrations ruleset."""

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
    """Contract tests for ServiceIntegrationsRuleset."""

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
# Model Validator Tests (our custom validation logic)
# =============================================================================


class TestServiceIntegrationsRulesetDataValidation:
    """Test our custom model validators on the ruleset data class."""

    def test_rejects_invalid_service_category(self) -> None:
        """Test that rules with service_category not in master list are rejected."""
        rule = ServiceIntegrationRule(
            name="invalid_rule",
            description="Rule with invalid service_category",
            patterns=("test",),
            service_category="invalid_service",
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

    def test_rejects_invalid_purpose_category(self) -> None:
        """Test that rules with purpose_category not in master list are rejected."""
        rule = ServiceIntegrationRule(
            name="invalid_rule",
            description="Rule with invalid purpose_category",
            patterns=("test",),
            service_category="cloud_infrastructure",
            purpose_category="INVALID_PURPOSE",
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
