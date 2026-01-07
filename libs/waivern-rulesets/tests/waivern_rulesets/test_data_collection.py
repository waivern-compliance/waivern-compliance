"""Unit tests for DataCollectionRuleset class."""

import pytest

from waivern_rulesets.base import AbstractRuleset
from waivern_rulesets.data_collection import (
    DataCollectionRule,
    DataCollectionRuleset,
)
from waivern_rulesets.testing import RulesetContractTests

# =============================================================================
# Contract Tests (inherited from RulesetContractTests)
# =============================================================================


class TestDataCollectionRulesetContract(RulesetContractTests[DataCollectionRule]):
    """Contract tests for DataCollectionRuleset.

    Inherits all standard ruleset contract tests automatically.

    """

    @pytest.fixture
    def ruleset_class(self) -> type[AbstractRuleset[DataCollectionRule]]:
        """Provide the ruleset class to test."""
        return DataCollectionRuleset

    @pytest.fixture
    def rule_class(self) -> type[DataCollectionRule]:
        """Provide the rule class used by the ruleset."""
        return DataCollectionRule

    @pytest.fixture
    def expected_name(self) -> str:
        """Provide the expected canonical name of the ruleset."""
        return "data_collection"


# =============================================================================
# Rule-specific Tests (unique to DataCollectionRule)
# =============================================================================


class TestDataCollectionRule:
    """Test cases for the DataCollectionRule class."""

    def test_data_collection_rule_with_all_fields(self) -> None:
        """Test DataCollectionRule with all fields."""
        rule = DataCollectionRule(
            name="form_data_rule",
            description="Form data collection rule",
            patterns=("$_POST", "form_data"),
            collection_type="form_data",
            data_source="http_post",
        )

        assert rule.name == "form_data_rule"
        assert rule.collection_type == "form_data"
        assert rule.data_source == "http_post"


# =============================================================================
# Ruleset-specific Tests
# =============================================================================


class TestDataCollectionRuleset:
    """Test cases for DataCollectionRuleset-specific behaviour."""

    def setup_method(self) -> None:
        """Set up test fixtures for each test method."""
        self.ruleset = DataCollectionRuleset()

    def test_rules_have_collection_type_and_data_source(self) -> None:
        """Test that all rules have collection_type and data_source fields."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert isinstance(rule.collection_type, str)
            assert isinstance(rule.data_source, str)
            assert len(rule.collection_type) > 0
            assert len(rule.data_source) > 0
