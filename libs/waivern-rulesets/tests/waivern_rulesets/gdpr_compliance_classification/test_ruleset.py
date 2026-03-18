"""Unit tests for GDPR compliance classification ruleset."""

import pytest
from pydantic import ValidationError

from waivern_rulesets import AbstractRuleset
from waivern_rulesets.gdpr_compliance_classification import (
    GDPRComplianceClassificationRule,
    GDPRComplianceClassificationRuleset,
)
from waivern_rulesets.gdpr_compliance_classification.ruleset import (
    GDPRComplianceClassificationRulesetData,
)
from waivern_rulesets.testing import RulesetContractTests

# =============================================================================
# Contract Tests (inherited from RulesetContractTests)
# =============================================================================


class TestGDPRComplianceClassificationRulesetContract(
    RulesetContractTests[GDPRComplianceClassificationRule]
):
    """Contract tests for GDPRComplianceClassificationRuleset."""

    @pytest.fixture
    def ruleset_class(
        self,
    ) -> type[AbstractRuleset[GDPRComplianceClassificationRule]]:
        """Provide the ruleset class to test."""
        return GDPRComplianceClassificationRuleset

    @pytest.fixture
    def rule_class(self) -> type[GDPRComplianceClassificationRule]:
        """Provide the rule class used by the ruleset."""
        return GDPRComplianceClassificationRule

    @pytest.fixture
    def expected_name(self) -> str:
        """Provide the expected canonical name of the ruleset."""
        return "gdpr_compliance_classification"


# =============================================================================
# Model Validator Tests (our custom validation logic)
# =============================================================================


class TestGDPRComplianceClassificationRulesetDataValidation:
    """Test our custom model validators on the ruleset data class."""

    def test_rejects_invalid_purpose_category(self) -> None:
        """Test that rules with purpose_category not in master list are rejected."""
        rule = GDPRComplianceClassificationRule(
            name="Invalid Rule",
            description="Test",
            purpose_category="invalid_category",
            article_references=("Article 6(1)(b)",),
            typical_lawful_bases=("contract",),
            indicator_purposes=("General Product and Service Delivery",),
        )

        with pytest.raises(ValidationError, match="invalid purpose_category"):
            GDPRComplianceClassificationRulesetData(
                name="test",
                version="1.0.0",
                description="Test",
                purpose_categories=["operational"],
                indicator_purposes=["General Product and Service Delivery"],
                rules=[rule],
            )

    def test_rejects_invalid_indicator_purposes(self) -> None:
        """Test that rules with indicator_purposes not in master list are rejected."""
        rule = GDPRComplianceClassificationRule(
            name="Invalid Rule",
            description="Test",
            purpose_category="operational",
            article_references=("Article 6(1)(b)",),
            typical_lawful_bases=("contract",),
            indicator_purposes=("Invalid Purpose",),
        )

        with pytest.raises(ValidationError, match="invalid indicator_purposes"):
            GDPRComplianceClassificationRulesetData(
                name="test",
                version="1.0.0",
                description="Test",
                purpose_categories=["operational"],
                indicator_purposes=["General Product and Service Delivery"],
                rules=[rule],
            )

    def test_rejects_sensitive_categories_not_in_purpose_categories(self) -> None:
        """Test that sensitive_categories must be subset of purpose_categories."""
        rule = GDPRComplianceClassificationRule(
            name="Test Rule",
            description="Test",
            purpose_category="operational",
            typical_lawful_bases=("contract",),
            indicator_purposes=("General Product and Service Delivery",),
        )

        with pytest.raises(ValidationError, match="invalid categories"):
            GDPRComplianceClassificationRulesetData(
                name="test",
                version="1.0.0",
                description="Test",
                purpose_categories=["operational"],
                indicator_purposes=["General Product and Service Delivery"],
                sensitive_categories=["ai_and_ml"],
                rules=[rule],
            )

    def test_rejects_inconsistent_sensitive_purpose_flag(self) -> None:
        """Test that sensitive_purpose must match sensitive_categories membership."""
        rule = GDPRComplianceClassificationRule(
            name="Inconsistent Rule",
            description="Test",
            purpose_category="ai_and_ml",
            typical_lawful_bases=("consent",),
            indicator_purposes=("Artificial Intelligence Model Training",),
            sensitive_purpose=False,  # Should be True since ai_and_ml is sensitive
        )

        with pytest.raises(ValidationError, match="sensitive_purpose"):
            GDPRComplianceClassificationRulesetData(
                name="test",
                version="1.0.0",
                description="Test",
                purpose_categories=["ai_and_ml"],
                indicator_purposes=["Artificial Intelligence Model Training"],
                sensitive_categories=["ai_and_ml"],
                rules=[rule],
            )


# =============================================================================
# Data Completeness Tests
# =============================================================================


class TestGDPRComplianceClassificationRulesetCompleteness:
    """Test that the actual YAML ruleset data is complete."""

    def test_all_indicator_purposes_are_mapped(self) -> None:
        """Test that all indicator purposes have classifications."""
        ruleset = GDPRComplianceClassificationRuleset()
        rules = ruleset.get_rules()

        all_mapped_purposes: set[str] = set()
        for rule in rules:
            all_mapped_purposes.update(rule.indicator_purposes)

        expected_purposes = {
            # From processing_purposes ruleset
            "Artificial Intelligence Model Training",
            "Artificial Intelligence Bias Testing",
            "Artificial Intelligence Model Refinement",
            "Artificial Intelligence Performance Testing",
            "Artificial Intelligence Security Testing",
            "Artificial Intelligence Compliance Management",
            "General Product and Service Delivery",
            "Customer Service and Support",
            "Customization of Products and Services",
            "User Identity and Login Management",
            "Payment, Billing, and Invoicing",
            "Behavioral Data Analysis for Product Improvement",
            "Dynamic Personalization of Products and Services",
            "Consumer Marketing Within Owned Products",
            "Targeted Marketing via Third-Party Platforms",
            "Third-Party Marketing via Owned Products",
            "Security, Fraud Prevention, and Abuse Detection",
            # From service_integrations ruleset
            "Cloud Infrastructure Services",
            "Communication Services",
            "Identity Management Services",
            "Payment Processing Services",
            "user_analytics",
            "social_media",
            "AI and ML Services",
            "Media Processing Services",
            "Messaging Platforms",
            "Healthcare Practice Management",
            # From data_collection ruleset
            "PHP POST Data Collection",
            "PHP GET Parameter Collection",
            "PHP Cookie Access",
            "PHP Session Data Access",
            "HTML Form Input Fields",
            "JavaScript Client Storage",
            "File Upload Processing",
            "SQL Database Queries",
            "Database Connections and ORM",
        }

        assert all_mapped_purposes == expected_purposes
