"""Unit tests for GDPR data collection classification ruleset."""

import pytest
from pydantic import ValidationError

from waivern_rulesets import AbstractRuleset
from waivern_rulesets.gdpr_data_collection_classification import (
    GDPRDataCollectionClassificationRule,
    GDPRDataCollectionClassificationRuleset,
)
from waivern_rulesets.gdpr_data_collection_classification.ruleset import (
    GDPRDataCollectionClassificationRulesetData,
)
from waivern_rulesets.testing import RulesetContractTests

# =============================================================================
# Contract Tests (inherited from RulesetContractTests)
# =============================================================================


class TestGDPRDataCollectionClassificationRulesetContract(
    RulesetContractTests[GDPRDataCollectionClassificationRule]
):
    """Contract tests for GDPRDataCollectionClassificationRuleset."""

    @pytest.fixture
    def ruleset_class(
        self,
    ) -> type[AbstractRuleset[GDPRDataCollectionClassificationRule]]:
        """Provide the ruleset class to test."""
        return GDPRDataCollectionClassificationRuleset

    @pytest.fixture
    def rule_class(self) -> type[GDPRDataCollectionClassificationRule]:
        """Provide the rule class used by the ruleset."""
        return GDPRDataCollectionClassificationRule

    @pytest.fixture
    def expected_name(self) -> str:
        """Provide the expected canonical name of the ruleset."""
        return "gdpr_data_collection_classification"


# =============================================================================
# Model Validator Tests (our custom validation logic)
# =============================================================================


class TestGDPRDataCollectionClassificationRulesetDataValidation:
    """Test our custom model validators on the ruleset data class."""

    def test_rejects_invalid_purpose_category(self) -> None:
        """Test that rules with purpose_category not in master list are rejected."""
        rule = GDPRDataCollectionClassificationRule(
            name="Invalid Rule",
            description="Test",
            purpose_category="invalid_category",
            article_references=("Article 5",),
            typical_lawful_bases=("contract",),
            indicator_collection_types=("form_data",),
        )

        with pytest.raises(ValidationError, match="invalid purpose_category"):
            GDPRDataCollectionClassificationRulesetData(
                name="test",
                version="1.0.0",
                description="Test",
                purpose_categories=["context_dependent"],
                indicator_collection_types=["form_data"],
                rules=[rule],
            )

    def test_rejects_invalid_indicator_collection_types(self) -> None:
        """Test that rules with indicator_collection_types not in master list are rejected."""
        rule = GDPRDataCollectionClassificationRule(
            name="Invalid Rule",
            description="Test",
            purpose_category="context_dependent",
            article_references=("Article 5",),
            typical_lawful_bases=("contract",),
            indicator_collection_types=("nonexistent_type",),
        )

        with pytest.raises(ValidationError, match="invalid indicator_collection_types"):
            GDPRDataCollectionClassificationRulesetData(
                name="test",
                version="1.0.0",
                description="Test",
                purpose_categories=["context_dependent"],
                indicator_collection_types=["form_data"],
                rules=[rule],
            )

    def test_rejects_sensitive_categories_not_in_purpose_categories(self) -> None:
        """Test that sensitive_categories must be subset of purpose_categories."""
        rule = GDPRDataCollectionClassificationRule(
            name="Test Rule",
            description="Test",
            purpose_category="context_dependent",
            typical_lawful_bases=("contract",),
            indicator_collection_types=("form_data",),
        )

        with pytest.raises(ValidationError, match="invalid categories"):
            GDPRDataCollectionClassificationRulesetData(
                name="test",
                version="1.0.0",
                description="Test",
                purpose_categories=["context_dependent"],
                indicator_collection_types=["form_data"],
                sensitive_categories=["ai_and_ml"],
                rules=[rule],
            )

    def test_rejects_inconsistent_sensitive_purpose_flag(self) -> None:
        """Test that sensitive_purpose must match sensitive_categories membership."""
        rule = GDPRDataCollectionClassificationRule(
            name="Inconsistent Rule",
            description="Test",
            purpose_category="context_dependent",
            typical_lawful_bases=("consent",),
            indicator_collection_types=("form_data",),
            sensitive_purpose=True,  # Should be False since context_dependent is not sensitive
        )

        with pytest.raises(ValidationError, match="sensitive_purpose"):
            GDPRDataCollectionClassificationRulesetData(
                name="test",
                version="1.0.0",
                description="Test",
                purpose_categories=["context_dependent"],
                indicator_collection_types=["form_data"],
                rules=[rule],
            )


# =============================================================================
# Data Completeness Tests
# =============================================================================


class TestGDPRDataCollectionClassificationRulesetCompleteness:
    """Test that the actual YAML ruleset data is complete."""

    def test_all_indicator_collection_types_are_mapped(self) -> None:
        """Test that all collection type slugs have classifications."""
        ruleset = GDPRDataCollectionClassificationRuleset()
        rules = ruleset.get_rules()

        all_mapped_types: set[str] = set()
        for rule in rules:
            all_mapped_types.update(rule.indicator_collection_types)

        expected_types = {
            "form_data",
            "url_parameters",
            "html_forms",
            "file_upload",
            "cookies",
            "session_data",
            "client_storage",
            "database_query",
            "database_connection",
        }

        assert all_mapped_types == expected_types
