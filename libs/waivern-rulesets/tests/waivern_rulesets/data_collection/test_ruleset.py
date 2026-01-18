"""Unit tests for DataCollectionRuleset class."""

import pytest
from pydantic import ValidationError

from waivern_rulesets import AbstractRuleset
from waivern_rulesets.data_collection import (
    DataCollectionRule,
    DataCollectionRuleset,
    DataCollectionRulesetData,
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
# RulesetData Validation Tests
# =============================================================================


class TestDataCollectionRulesetData:
    """Test cases for the DataCollectionRulesetData class."""

    def test_ruleset_data_with_valid_categories(self) -> None:
        """Test DataCollectionRulesetData with valid categories passes validation."""
        rule = DataCollectionRule(
            name="form_rule",
            description="Form data collection",
            patterns=("$_POST",),
            collection_type="form_data",
            data_source="http_post",
        )

        ruleset_data = DataCollectionRulesetData(
            name="data_collection",
            version="1.0.0",
            description="Test ruleset",
            collection_type_categories=["form_data", "cookie_data"],
            data_source_categories=["http_post", "http_get"],
            rules=[rule],
        )

        assert len(ruleset_data.rules) == 1
        assert ruleset_data.rules[0].collection_type == "form_data"

    def test_ruleset_data_rejects_invalid_collection_type(self) -> None:
        """Test DataCollectionRulesetData rejects invalid collection_type."""
        rule = DataCollectionRule(
            name="invalid_rule",
            description="Rule with invalid collection_type",
            patterns=("test",),
            collection_type="invalid_type",  # Not in master list
            data_source="http_post",
        )

        with pytest.raises(ValidationError, match="invalid collection_type"):
            DataCollectionRulesetData(
                name="data_collection",
                version="1.0.0",
                description="Test ruleset",
                collection_type_categories=["form_data", "cookie_data"],
                data_source_categories=["http_post", "http_get"],
                rules=[rule],
            )

    def test_ruleset_data_rejects_invalid_data_source(self) -> None:
        """Test DataCollectionRulesetData rejects invalid data_source."""
        rule = DataCollectionRule(
            name="invalid_rule",
            description="Rule with invalid data_source",
            patterns=("test",),
            collection_type="form_data",
            data_source="invalid_source",  # Not in master list
        )

        with pytest.raises(ValidationError, match="invalid data_source"):
            DataCollectionRulesetData(
                name="data_collection",
                version="1.0.0",
                description="Test ruleset",
                collection_type_categories=["form_data", "cookie_data"],
                data_source_categories=["http_post", "http_get"],
                rules=[rule],
            )


# =============================================================================
# Ruleset-specific Tests
# =============================================================================


class TestDataCollectionRuleset:
    """Test cases for DataCollectionRuleset-specific behaviour."""

    @pytest.fixture
    def ruleset(self) -> DataCollectionRuleset:
        """Provide a DataCollectionRuleset instance for testing."""
        return DataCollectionRuleset()

    def test_rules_have_collection_type_and_data_source(
        self, ruleset: DataCollectionRuleset
    ) -> None:
        """Test that all rules have collection_type and data_source fields."""
        rules = ruleset.get_rules()

        for rule in rules:
            assert isinstance(rule.collection_type, str)
            assert isinstance(rule.data_source, str)
            assert len(rule.collection_type) > 0
            assert len(rule.data_source) > 0
