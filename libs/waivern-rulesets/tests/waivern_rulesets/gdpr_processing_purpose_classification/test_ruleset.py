"""Unit tests for GDPR processing purpose classification ruleset."""

import pytest
from pydantic import ValidationError

from waivern_rulesets import AbstractRuleset
from waivern_rulesets.gdpr_processing_purpose_classification import (
    GDPRProcessingPurposeClassificationRule,
    GDPRProcessingPurposeClassificationRuleset,
)
from waivern_rulesets.gdpr_processing_purpose_classification.ruleset import (
    GDPRProcessingPurposeClassificationRulesetData,
)
from waivern_rulesets.testing import RulesetContractTests

# =============================================================================
# Contract Tests (inherited from RulesetContractTests)
# =============================================================================


class TestGDPRProcessingPurposeClassificationRulesetContract(
    RulesetContractTests[GDPRProcessingPurposeClassificationRule]
):
    """Contract tests for GDPRProcessingPurposeClassificationRuleset."""

    @pytest.fixture
    def ruleset_class(
        self,
    ) -> type[AbstractRuleset[GDPRProcessingPurposeClassificationRule]]:
        """Provide the ruleset class to test."""
        return GDPRProcessingPurposeClassificationRuleset

    @pytest.fixture
    def rule_class(self) -> type[GDPRProcessingPurposeClassificationRule]:
        """Provide the rule class used by the ruleset."""
        return GDPRProcessingPurposeClassificationRule

    @pytest.fixture
    def expected_name(self) -> str:
        """Provide the expected canonical name of the ruleset."""
        return "gdpr_processing_purpose_classification"


# =============================================================================
# Field Validator Tests (our custom code)
# =============================================================================


class TestGDPRProcessingPurposeClassificationRule:
    """Test our custom field validators on the rule class."""

    def test_rule_converts_lists_to_tuples(self) -> None:
        """Test that list fields are converted to tuples for immutability."""
        rule = GDPRProcessingPurposeClassificationRule(
            name="Test Rule",
            description="Test",
            purpose_category="operational",
            article_references=["Article 6(1)(b)"],
            typical_lawful_bases=["contract"],  # type: ignore[arg-type]
            indicator_purposes=["General Product and Service Delivery"],  # type: ignore[arg-type]
            sensitive_purpose=False,
            dpia_recommendation="not_required",
        )

        assert isinstance(rule.typical_lawful_bases, tuple)
        assert isinstance(rule.indicator_purposes, tuple)


# =============================================================================
# Model Validator Tests (our custom validation logic)
# =============================================================================


class TestGDPRProcessingPurposeClassificationRulesetDataValidation:
    """Test our custom model validators on the ruleset data class."""

    def test_rejects_invalid_purpose_category(self) -> None:
        """Test that rules with purpose_category not in master list are rejected."""
        rule = GDPRProcessingPurposeClassificationRule(
            name="Invalid Rule",
            description="Test",
            purpose_category="invalid_category",
            article_references=["Article 6(1)(b)"],
            typical_lawful_bases=("contract",),
            indicator_purposes=("General Product and Service Delivery",),
        )

        with pytest.raises(ValidationError, match="invalid purpose_category"):
            GDPRProcessingPurposeClassificationRulesetData(
                name="test",
                version="1.0.0",
                description="Test",
                purpose_categories=["operational"],
                indicator_purposes=["General Product and Service Delivery"],
                rules=[rule],
            )

    def test_rejects_invalid_indicator_purposes(self) -> None:
        """Test that rules with indicator_purposes not in master list are rejected."""
        rule = GDPRProcessingPurposeClassificationRule(
            name="Invalid Rule",
            description="Test",
            purpose_category="operational",
            article_references=["Article 6(1)(b)"],
            typical_lawful_bases=("contract",),
            indicator_purposes=("Invalid Purpose",),
        )

        with pytest.raises(ValidationError, match="invalid indicator_purposes"):
            GDPRProcessingPurposeClassificationRulesetData(
                name="test",
                version="1.0.0",
                description="Test",
                purpose_categories=["operational"],
                indicator_purposes=["General Product and Service Delivery"],
                rules=[rule],
            )

    def test_rejects_sensitive_categories_not_in_purpose_categories(self) -> None:
        """Test that sensitive_categories must be subset of purpose_categories."""
        rule = GDPRProcessingPurposeClassificationRule(
            name="Test Rule",
            description="Test",
            purpose_category="operational",
            typical_lawful_bases=("contract",),
            indicator_purposes=("General Product and Service Delivery",),
        )

        with pytest.raises(ValidationError, match="invalid categories"):
            GDPRProcessingPurposeClassificationRulesetData(
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
        rule = GDPRProcessingPurposeClassificationRule(
            name="Inconsistent Rule",
            description="Test",
            purpose_category="ai_and_ml",
            typical_lawful_bases=("consent",),
            indicator_purposes=("Artificial Intelligence Model Training",),
            sensitive_purpose=False,  # Should be True since ai_and_ml is sensitive
        )

        with pytest.raises(ValidationError, match="sensitive_purpose"):
            GDPRProcessingPurposeClassificationRulesetData(
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


class TestGDPRProcessingPurposeClassificationRulesetCompleteness:
    """Test that the actual YAML ruleset data is complete."""

    def test_all_17_purposes_are_mapped(self) -> None:
        """Test that all 17 processing purposes have classifications."""
        ruleset = GDPRProcessingPurposeClassificationRuleset()
        rules = ruleset.get_rules()

        all_mapped_purposes: set[str] = set()
        for rule in rules:
            all_mapped_purposes.update(rule.indicator_purposes)

        expected_purposes = {
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
        }

        assert all_mapped_purposes == expected_purposes
