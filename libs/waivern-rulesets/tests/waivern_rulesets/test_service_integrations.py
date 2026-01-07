"""Tests for service integrations ruleset."""

import pytest

from waivern_rulesets.base import AbstractRuleset
from waivern_rulesets.service_integrations import (
    ServiceIntegrationRule,
    ServiceIntegrationsRuleset,
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
# Ruleset-specific Tests
# =============================================================================


class TestServiceIntegrationsRuleset:
    """Test cases for ServiceIntegrationsRuleset-specific behaviour."""

    def setup_method(self) -> None:
        """Set up test fixtures for each test method."""
        self.ruleset = ServiceIntegrationsRuleset()

    def test_rules_have_service_category_and_purpose_category(self) -> None:
        """Test that all rules have service_category and purpose_category fields."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert isinstance(rule.service_category, str)
            assert len(rule.service_category) > 0
            assert isinstance(rule.purpose_category, str)
            assert len(rule.purpose_category) > 0
