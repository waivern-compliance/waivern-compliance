"""Data collection ruleset.

This module defines patterns for detecting data collection mechanisms
in source code, such as HTTP form data, cookies, sessions, and API endpoints.
All patterns use simple string matching for human readability and easy maintenance.
"""

from typing import ClassVar

from pydantic import Field, model_validator
from waivern_core import DetectionRule, RulesetData

from waivern_rulesets.core.base import YAMLRuleset


class DataCollectionRule(DetectionRule):
    """Data collection rule with collection type and source."""

    collection_type: str = Field(description="Type of data collection")
    data_source: str = Field(description="Source of the data")


class DataCollectionRulesetData(RulesetData[DataCollectionRule]):
    """Data collection ruleset data model."""

    # Ruleset-specific properties
    collection_type_categories: list[str] = Field(
        min_length=1, description="Master list of valid data collection type categories"
    )
    data_source_categories: list[str] = Field(
        min_length=1, description="Master list of valid data source categories"
    )

    @model_validator(mode="after")
    def validate_rule_categories(self) -> "DataCollectionRulesetData":
        """Validate all rule collection_type and data_source values against master lists."""
        valid_collection_types = set(self.collection_type_categories)
        valid_data_sources = set(self.data_source_categories)

        for rule in self.rules:
            if rule.collection_type not in valid_collection_types:
                raise ValueError(
                    f"Rule '{rule.name}' has invalid collection_type '{rule.collection_type}'. Valid: {valid_collection_types}"
                )
            if rule.data_source not in valid_data_sources:
                raise ValueError(
                    f"Rule '{rule.name}' has invalid data_source '{rule.data_source}'. Valid: {valid_data_sources}"
                )
        return self


class DataCollectionRuleset(YAMLRuleset[DataCollectionRule]):
    """Ruleset for detecting data collection patterns in source code."""

    ruleset_name: ClassVar[str] = "data_collection"
    ruleset_version: ClassVar[str] = "1.0.0"
    _data_class: ClassVar[  # pyright: ignore[reportIncompatibleVariableOverride]
        type[DataCollectionRulesetData]
    ] = DataCollectionRulesetData
