"""Unit tests for data collection ruleset."""

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
    """Contract tests for DataCollectionRuleset."""

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
# Model Validator Tests (our custom validation logic)
# =============================================================================


class TestDataCollectionRulesetDataValidation:
    """Test our custom model validators on the ruleset data class."""

    def test_rejects_invalid_collection_type(self) -> None:
        """Test that rules with collection_type not in master list are rejected."""
        rule = DataCollectionRule(
            name="invalid_rule",
            description="Rule with invalid collection_type",
            patterns=("test",),
            collection_type="invalid_type",
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

    def test_rejects_invalid_data_source(self) -> None:
        """Test that rules with data_source not in master list are rejected."""
        rule = DataCollectionRule(
            name="invalid_rule",
            description="Rule with invalid data_source",
            patterns=("test",),
            collection_type="form_data",
            data_source="invalid_source",
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
