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
# RulesetData Validation Tests
# =============================================================================


class TestProcessingPurposesRulesetData:
    """Test cases for the ProcessingPurposesRulesetData class.

    The processing purposes ruleset maintains a pre-defined list of valid
    processing purpose names (the `purposes` field). Each rule's `name` must
    match an entry in this list. This ensures consistency and prevents typos
    in purpose names, as the rule name becomes the `purpose` field in findings.
    """

    def test_processing_purposes_ruleset_accepts_valid_data(self) -> None:
        """Test ProcessingPurposesRulesetData accepts valid ruleset structure.

        A valid ruleset has:
        - A `purposes` list defining all valid processing purpose names
        - Rules whose `name` fields match entries in the `purposes` list
        """
        # Arrange - rule name matches an entry in purposes list
        rule = ProcessingPurposeRule(
            name="Payment Processing",
            description="Detects payment-related purposes",
            patterns=("payment", "billing"),
        )

        # Act
        ruleset_data = ProcessingPurposesRulesetData(
            name="test_ruleset",
            version="1.0.0",
            description="Test ruleset",
            purposes=["Payment Processing", "Analytics"],
            rules=[rule],
        )

        # Assert
        assert len(ruleset_data.rules) == 1
        assert "Payment Processing" in ruleset_data.purposes
        assert "Analytics" in ruleset_data.purposes

    def test_processing_purposes_ruleset_rejects_rule_with_unknown_purpose_name(
        self,
    ) -> None:
        """Test ProcessingPurposesRulesetData rejects rules with names not in purposes list.

        This validation prevents typos and ensures all rules map to a known
        processing purpose. The rule's `name` is used as the `purpose` field
        in findings, so it must be a recognised value.
        """
        # Arrange - rule name NOT in purposes list (typo or unknown purpose)
        rule = ProcessingPurposeRule(
            name="Unknown Purpose",
            description="This purpose is not in the allowed list",
            patterns=("unknown",),
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="not in purposes"):
            _ = ProcessingPurposesRulesetData(
                name="test_ruleset",
                version="1.0.0",
                description="Test ruleset",
                purposes=["Payment Processing", "Analytics"],
                rules=[rule],
            )


# =============================================================================
# Ruleset-specific Tests
# =============================================================================


class TestProcessingPurposesRuleset:
    """Test cases for ProcessingPurposesRuleset-specific behaviour."""

    @pytest.fixture
    def ruleset(self) -> ProcessingPurposesRuleset:
        """Provide a ProcessingPurposesRuleset instance for testing."""
        return ProcessingPurposesRuleset()
