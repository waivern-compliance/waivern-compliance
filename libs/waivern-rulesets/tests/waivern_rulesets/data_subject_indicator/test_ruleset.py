"""Unit tests for data subject indicator ruleset."""

import pytest
from pydantic import ValidationError

from waivern_rulesets import AbstractRuleset
from waivern_rulesets.data_subject_indicator import (
    DataSubjectIndicatorRule,
    DataSubjectIndicatorRuleset,
    DataSubjectIndicatorRulesetData,
)
from waivern_rulesets.testing import RulesetContractTests

# =============================================================================
# Contract Tests (inherited from RulesetContractTests)
# =============================================================================


class TestDataSubjectIndicatorRulesetContract(
    RulesetContractTests[DataSubjectIndicatorRule]
):
    """Contract tests for DataSubjectIndicatorRuleset."""

    @pytest.fixture
    def ruleset_class(self) -> type[AbstractRuleset[DataSubjectIndicatorRule]]:
        """Provide the ruleset class to test."""
        return DataSubjectIndicatorRuleset

    @pytest.fixture
    def rule_class(self) -> type[DataSubjectIndicatorRule]:
        """Provide the rule class used by the ruleset."""
        return DataSubjectIndicatorRule

    @pytest.fixture
    def expected_name(self) -> str:
        """Provide the expected canonical name of the ruleset."""
        return "data_subject_indicator"


# =============================================================================
# Model Validator Tests (our custom validation logic)
# =============================================================================


class TestDataSubjectIndicatorRulesetDataValidation:
    """Test our custom model validators on the ruleset data class."""

    def test_rejects_invalid_subject_category(self) -> None:
        """Test that rules with subject_category not in master list are rejected."""
        rule = DataSubjectIndicatorRule(
            name="invalid_rule",
            description="Rule with invalid category",
            patterns=("test",),
            subject_category="invalid_category",
            indicator_type="primary",
            confidence_weight=40,
        )

        with pytest.raises(ValidationError, match="invalid subject_category"):
            DataSubjectIndicatorRulesetData(
                name="data_subjects",
                version="1.0.0",
                description="Data subject classification ruleset",
                subject_categories=["employee", "customer"],
                risk_increasing_modifiers=["minor"],
                risk_decreasing_modifiers=["non-EU-resident"],
                rules=[rule],
            )

    def test_rejects_duplicate_rule_names(self) -> None:
        """Test that duplicate rule names are rejected."""
        rule1 = DataSubjectIndicatorRule(
            name="duplicate_name",
            description="First rule",
            patterns=("test1",),
            subject_category="employee",
            indicator_type="primary",
            confidence_weight=40,
        )

        rule2 = DataSubjectIndicatorRule(
            name="duplicate_name",
            description="Second rule",
            patterns=("test2",),
            subject_category="customer",
            indicator_type="secondary",
            confidence_weight=20,
        )

        with pytest.raises(ValidationError, match="Duplicate rule names found"):
            DataSubjectIndicatorRulesetData(
                name="data_subjects",
                version="1.0.0",
                description="Test ruleset",
                subject_categories=["employee", "customer"],
                risk_increasing_modifiers=["minor"],
                risk_decreasing_modifiers=["non-EU-resident"],
                rules=[rule1, rule2],
            )
