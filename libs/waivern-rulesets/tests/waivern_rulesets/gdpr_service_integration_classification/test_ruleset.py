"""Unit tests for GDPR service integration classification ruleset."""

import pytest
from pydantic import ValidationError

from waivern_rulesets import AbstractRuleset
from waivern_rulesets.gdpr_service_integration_classification import (
    GDPRServiceIntegrationClassificationRule,
    GDPRServiceIntegrationClassificationRuleset,
)
from waivern_rulesets.gdpr_service_integration_classification.ruleset import (
    GDPRServiceIntegrationClassificationRulesetData,
)
from waivern_rulesets.service_integrations import ServiceIntegrationsRuleset
from waivern_rulesets.testing import RulesetContractTests

# =============================================================================
# Contract Tests (inherited from RulesetContractTests)
# =============================================================================


class TestGDPRServiceIntegrationClassificationRulesetContract(
    RulesetContractTests[GDPRServiceIntegrationClassificationRule]
):
    """Contract tests for GDPRServiceIntegrationClassificationRuleset."""

    @pytest.fixture
    def ruleset_class(
        self,
    ) -> type[AbstractRuleset[GDPRServiceIntegrationClassificationRule]]:
        """Provide the ruleset class to test."""
        return GDPRServiceIntegrationClassificationRuleset

    @pytest.fixture
    def rule_class(self) -> type[GDPRServiceIntegrationClassificationRule]:
        """Provide the rule class used by the ruleset."""
        return GDPRServiceIntegrationClassificationRule

    @pytest.fixture
    def expected_name(self) -> str:
        """Provide the expected canonical name of the ruleset."""
        return "gdpr_service_integration_classification"


# =============================================================================
# Model Validator Tests (our custom validation logic)
# =============================================================================


class TestGDPRServiceIntegrationClassificationRulesetDataValidation:
    """Test our custom model validators on the ruleset data class."""

    def test_rejects_invalid_purpose_category(self) -> None:
        """Test that rules with purpose_category not in master list are rejected."""
        rule = GDPRServiceIntegrationClassificationRule(
            name="Invalid Rule",
            description="Test",
            purpose_category="invalid_category",
            article_references=("Article 28",),
            typical_lawful_bases=("contract",),
            indicator_service_categories=("cloud_infrastructure",),
        )

        with pytest.raises(ValidationError, match="invalid purpose_category"):
            GDPRServiceIntegrationClassificationRulesetData(
                name="test",
                version="1.0.0",
                description="Test",
                purpose_categories=["operational"],
                indicator_service_categories=["cloud_infrastructure"],
                rules=[rule],
            )

    def test_rejects_invalid_indicator_service_categories(self) -> None:
        """Test that rules with indicator_service_categories not in master list are rejected."""
        rule = GDPRServiceIntegrationClassificationRule(
            name="Invalid Rule",
            description="Test",
            purpose_category="operational",
            article_references=("Article 28",),
            typical_lawful_bases=("contract",),
            indicator_service_categories=("nonexistent_service",),
        )

        with pytest.raises(
            ValidationError, match="invalid indicator_service_categories"
        ):
            GDPRServiceIntegrationClassificationRulesetData(
                name="test",
                version="1.0.0",
                description="Test",
                purpose_categories=["operational"],
                indicator_service_categories=["cloud_infrastructure"],
                rules=[rule],
            )

    def test_rejects_sensitive_categories_not_in_purpose_categories(self) -> None:
        """Test that sensitive_categories must be subset of purpose_categories."""
        rule = GDPRServiceIntegrationClassificationRule(
            name="Test Rule",
            description="Test",
            purpose_category="operational",
            typical_lawful_bases=("contract",),
            indicator_service_categories=("cloud_infrastructure",),
        )

        with pytest.raises(ValidationError, match="invalid categories"):
            GDPRServiceIntegrationClassificationRulesetData(
                name="test",
                version="1.0.0",
                description="Test",
                purpose_categories=["operational"],
                indicator_service_categories=["cloud_infrastructure"],
                sensitive_categories=["ai_and_ml"],
                rules=[rule],
            )

    def test_rejects_inconsistent_sensitive_purpose_flag(self) -> None:
        """Test that sensitive_purpose must match sensitive_categories membership."""
        rule = GDPRServiceIntegrationClassificationRule(
            name="Inconsistent Rule",
            description="Test",
            purpose_category="ai_and_ml",
            typical_lawful_bases=("consent",),
            indicator_service_categories=("ai_ml_services",),
            sensitive_purpose=False,  # Should be True since ai_and_ml is sensitive
        )

        with pytest.raises(ValidationError, match="sensitive_purpose"):
            GDPRServiceIntegrationClassificationRulesetData(
                name="test",
                version="1.0.0",
                description="Test",
                purpose_categories=["ai_and_ml"],
                indicator_service_categories=["ai_ml_services"],
                sensitive_categories=["ai_and_ml"],
                rules=[rule],
            )


# =============================================================================
# Data Completeness Tests
# =============================================================================


class TestGDPRServiceIntegrationClassificationRulesetCompleteness:
    """Test that the actual YAML ruleset data is complete."""

    def test_all_service_categories_are_classified(self) -> None:
        """Test that every service category from the service_integrations ruleset has a classification."""
        all_service_categories: set[str] = {
            rule.service_category for rule in ServiceIntegrationsRuleset().get_rules()
        }

        classification_ruleset = GDPRServiceIntegrationClassificationRuleset()
        mapped_categories: set[str] = {
            category
            for rule in classification_ruleset.get_rules()
            for category in rule.indicator_service_categories
        }

        uncovered = all_service_categories - mapped_categories
        assert not uncovered, (
            f"Service categories not covered by any GDPR classification rule: {uncovered}"
        )
