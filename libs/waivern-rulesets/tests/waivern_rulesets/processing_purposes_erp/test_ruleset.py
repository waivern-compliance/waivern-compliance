"""Unit tests for processing purposes ERP extension ruleset."""

import pytest

from waivern_rulesets import AbstractRuleset
from waivern_rulesets.processing_purposes import ProcessingPurposeRule
from waivern_rulesets.processing_purposes_erp import ProcessingPurposesERPRuleset
from waivern_rulesets.testing import RulesetContractTests

# =============================================================================
# Contract Tests (inherited from RulesetContractTests)
# =============================================================================


class TestProcessingPurposesERPRulesetContract(
    RulesetContractTests[ProcessingPurposeRule]
):
    """Contract tests for ProcessingPurposesERPRuleset."""

    @pytest.fixture
    def ruleset_class(self) -> type[AbstractRuleset[ProcessingPurposeRule]]:
        """Provide the ruleset class to test."""
        return ProcessingPurposesERPRuleset

    @pytest.fixture
    def rule_class(self) -> type[ProcessingPurposeRule]:
        """Provide the rule class used by the ruleset."""
        return ProcessingPurposeRule

    @pytest.fixture
    def expected_name(self) -> str:
        """Provide the expected canonical name of the ruleset."""
        return "processing_purposes_erp"


# =============================================================================
# ERP pattern presence
# =============================================================================


class TestProcessingPurposesERPPatterns:
    """Verify that the ERP ruleset contains the expected Dolibarr-specific patterns."""

    def test_erp_patterns_are_present_in_erp_ruleset(self) -> None:
        """Verify all Dolibarr-specific patterns are present in the ERP ruleset."""
        ruleset = ProcessingPurposesERPRuleset()
        all_patterns = {p for rule in ruleset.get_rules() for p in rule.patterns}

        expected_erp_patterns = {
            # audit_logging
            "useractivity",
            "addEvent",
            # access_control_management
            "restrictedArea",
            "verifCond",
            "checkUserAccess",
            "llx_rights",
            "llx_user_rights",
        }
        assert expected_erp_patterns <= all_patterns
