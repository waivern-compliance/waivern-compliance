"""Unit tests for processing purposes ruleset."""

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
    """Contract tests for ProcessingPurposesRuleset."""

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
# Model Validator Tests (our custom validation logic)
# =============================================================================


class TestProcessingPurposesRulesetDataValidation:
    """Test our custom model validators on the ruleset data class.

    The processing purposes ruleset maintains a pre-defined list of valid
    processing purpose names (the `purposes` field). Each rule's `name` must
    match an entry in this list to prevent typos and ensure consistency.
    """

    def test_rejects_rule_with_unknown_purpose_name(self) -> None:
        """Test that rules with names not in purposes list are rejected."""
        rule = ProcessingPurposeRule(
            name="Unknown Purpose",
            purpose="unknown_purpose",
            description="This purpose is not in the allowed list",
            patterns=("unknown",),
        )

        with pytest.raises(ValidationError, match="not in purposes"):
            ProcessingPurposesRulesetData(
                name="test_ruleset",
                version="1.0.0",
                description="Test ruleset",
                purposes=["Payment Processing", "Analytics"],
                purpose_slugs=["payment_processing", "analytics"],
                rules=[rule],
            )

    def test_rejects_rule_with_unknown_purpose_slug(self) -> None:
        """Test that rules with purpose slugs not in purpose_slugs list are rejected."""
        rule = ProcessingPurposeRule(
            name="Payment Processing",
            purpose="unknown_slug",
            description="Rule with a slug not in the allowed list",
            patterns=("payment",),
        )

        with pytest.raises(ValidationError, match="not in purpose_slugs"):
            ProcessingPurposesRulesetData(
                name="test_ruleset",
                version="1.0.0",
                description="Test ruleset",
                purposes=["Payment Processing"],
                purpose_slugs=["payment_processing"],
                rules=[rule],
            )

    def test_purpose_slug_from_loaded_ruleset_is_snake_case(self) -> None:
        """Test that loaded rules expose snake_case purpose slugs, not full names."""
        ruleset = ProcessingPurposesRuleset()
        rules = ruleset.get_rules()

        assert len(rules) > 0
        for rule in rules:
            assert rule.purpose == rule.purpose.lower(), (
                f"Purpose slug '{rule.purpose}' should be lowercase"
            )
            assert " " not in rule.purpose, (
                f"Purpose slug '{rule.purpose}' should not contain spaces"
            )
