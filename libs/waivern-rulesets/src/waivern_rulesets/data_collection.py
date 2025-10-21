"""Data collection ruleset.

This module defines patterns for detecting data collection mechanisms
in source code, such as HTTP form data, cookies, sessions, and API endpoints.
All patterns use simple string matching for human readability and easy maintenance.
"""

import logging
from pathlib import Path
from typing import Final, override

import yaml
from pydantic import Field, model_validator
from waivern_core import BaseRule, RulesetData

from waivern_rulesets.base import AbstractRuleset

logger = logging.getLogger(__name__)

# Version constant for this ruleset and its data (private)
_RULESET_DATA_VERSION: Final[str] = "1.0.0"


class DataCollectionRule(BaseRule):
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


_RULESET_NAME: Final[str] = "data_collection"


class DataCollectionRuleset(AbstractRuleset[DataCollectionRule]):
    """Ruleset for detecting data collection patterns in source code."""

    def __init__(self) -> None:
        """Initialise the data collection patterns ruleset."""
        self._rules: tuple[DataCollectionRule, ...] | None = None
        logger.debug(f"Initialised {self.name} ruleset version {self.version}")

    @property
    @override
    def name(self) -> str:
        """Get the canonical name of this ruleset."""
        return _RULESET_NAME

    @property
    @override
    def version(self) -> str:
        """Get the version of this ruleset."""
        return _RULESET_DATA_VERSION

    @override
    def get_rules(self) -> tuple[DataCollectionRule, ...]:
        """Get the data collection patterns rules.

        Returns:
            Immutable tuple of Rule objects containing all data collection patterns

        """
        if self._rules is None:
            # Load from YAML file with Pydantic validation
            yaml_file = (
                Path(__file__).parent
                / "data"
                / _RULESET_NAME
                / _RULESET_DATA_VERSION
                / f"{_RULESET_NAME}.yaml"
            )
            with yaml_file.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            ruleset_data = DataCollectionRulesetData.model_validate(data)
            self._rules = tuple(ruleset_data.rules)
            logger.debug(f"Loaded {len(self._rules)} data collection ruleset data")

        return self._rules
