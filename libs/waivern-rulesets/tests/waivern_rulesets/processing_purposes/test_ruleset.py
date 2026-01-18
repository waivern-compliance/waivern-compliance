"""Unit tests for ProcessingPurposesRuleset class."""

import pytest
from pydantic import ValidationError

from waivern_rulesets import AbstractRuleset
from waivern_rulesets.processing_purposes import (
    ProcessingPurposeRule,
    ProcessingPurposesRuleset,
    ProcessingPurposesRulesetData,
)
from waivern_rulesets.testing import RulesetContractTests

# =============================================================================
# Contract Tests (inherited from RulesetContractTests)
# =============================================================================


class TestProcessingPurposesRulesetContract(
    RulesetContractTests[ProcessingPurposeRule]
):
    """Contract tests for ProcessingPurposesRuleset.

    Inherits all standard ruleset contract tests automatically.

    """

    @pytest.fixture
    def ruleset_class(self) -> type[AbstractRuleset[ProcessingPurposeRule]]:
        """Provide the ruleset class to test."""
        return ProcessingPurposesRuleset

    @pytest.fixture
    def rule_class(self) -> type[ProcessingPurposeRule]:
        """Provide the rule class used by the ruleset."""
        return ProcessingPurposeRule

    @pytest.fixture
    def expected_name(self) -> str:
        """Provide the expected canonical name of the ruleset."""
        return "processing_purposes"


# =============================================================================
# Rule-specific Tests (unique to ProcessingPurposeRule)
# =============================================================================


class TestProcessingPurposeRule:
    """Test cases for the ProcessingPurposeRule class."""

    def test_processing_purpose_rule_with_all_fields(self) -> None:
        """Test ProcessingPurposeRule with all fields."""
        rule = ProcessingPurposeRule(
            name="analytics_rule",
            description="Analytics processing rule",
            patterns=("analytics", "tracking"),
            purpose_category="analytics",
        )

        assert rule.name == "analytics_rule"
        assert rule.purpose_category == "analytics"


# =============================================================================
# RulesetData Validation Tests
# =============================================================================


class TestProcessingPurposesRulesetData:
    """Test cases for the ProcessingPurposesRulesetData class."""

    def test_processing_purposes_ruleset_validation(self) -> None:
        """Test ProcessingPurposesRulesetData validates categories correctly."""
        rule = ProcessingPurposeRule(
            name="test_rule",
            description="Test rule",
            patterns=("test",),
            purpose_category="ANALYTICS",
        )

        ruleset = ProcessingPurposesRulesetData(
            name="test_ruleset",
            version="1.0.0",
            description="Test ruleset",
            purpose_categories=["ANALYTICS", "OPERATIONAL"],
            sensitive_categories=["ANALYTICS"],
            rules=[rule],
        )

        assert len(ruleset.rules) == 1
        assert "ANALYTICS" in ruleset.sensitive_categories
        assert "OPERATIONAL" in ruleset.purpose_categories

    def test_processing_purposes_ruleset_invalid_category(self) -> None:
        """Test ProcessingPurposesRulesetData rejects invalid rule categories."""
        rule = ProcessingPurposeRule(
            name="test_rule",
            description="Test rule",
            patterns=("test",),
            purpose_category="INVALID_CATEGORY",
        )

        with pytest.raises(ValidationError, match="invalid purpose_category"):
            ProcessingPurposesRulesetData(
                name="test_ruleset",
                version="1.0.0",
                description="Test ruleset",
                purpose_categories=["ANALYTICS", "OPERATIONAL"],
                rules=[rule],
            )

    def test_processing_purposes_sensitive_categories_subset_validation(self) -> None:
        """Test sensitive_categories must be subset of purpose_categories."""
        with pytest.raises(
            ValidationError, match="must be subset of purpose_categories"
        ):
            ProcessingPurposesRulesetData(
                name="test_ruleset",
                version="1.0.0",
                description="Test ruleset",
                purpose_categories=["ANALYTICS"],
                sensitive_categories=["INVALID_SENSITIVE"],
                rules=[],
            )


# =============================================================================
# Ruleset-specific Tests
# =============================================================================


class TestProcessingPurposesRuleset:
    """Test cases for ProcessingPurposesRuleset-specific behaviour."""

    def setup_method(self) -> None:
        """Set up test fixtures for each test method."""
        self.ruleset = ProcessingPurposesRuleset()

    def test_rules_have_purpose_category_field(self) -> None:
        """Test that all rules have purpose_category field."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert isinstance(rule.purpose_category, str)
            assert len(rule.purpose_category) > 0
