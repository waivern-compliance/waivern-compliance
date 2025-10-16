"""Personal data detection ruleset.

This module defines a ruleset for detecting personal data patterns.
It serves as a base for compliance with GDPR and other privacy regulations.
"""

import logging
from pathlib import Path
from typing import Final, override

import yaml
from pydantic import Field, ValidationInfo, field_validator, model_validator

from waivern_community.rulesets.base import AbstractRuleset
from waivern_community.rulesets.types import BaseRule, RulesetData

logger = logging.getLogger(__name__)

# Version constant for this ruleset and its data (private)
_RULESET_DATA_VERSION: Final[str] = "1.0.0"
_RULESET_NAME: Final[str] = "personal_data"


class PersonalDataRule(BaseRule):
    """Personal data rule with GDPR categories."""

    data_type: str = Field(description="Type of personal data this rule detects")
    special_category: bool = Field(
        default=False,
        description="Whether this is GDPR Article 9 special category data",
    )


class PersonalDataRulesetData(RulesetData[PersonalDataRule]):
    """Personal data ruleset with GDPR Article 9 support."""

    # Ruleset-specific properties
    data_type_categories: list[str] = Field(
        min_length=1,
        description="Master list of valid personal data type categories based on GDPR requirements",
    )
    special_category_types: list[str] = Field(
        default_factory=list,
        description="Subset of data_type_categories that are GDPR Article 9 special category types",
    )

    @field_validator("special_category_types")
    @classmethod
    def validate_special_categories_subset(
        cls, v: list[str], info: ValidationInfo
    ) -> list[str]:
        """Ensure special_category_types is subset of data_type_categories."""
        data_type_categories = info.data.get("data_type_categories", [])
        invalid = [cat for cat in v if cat not in data_type_categories]
        if invalid:
            raise ValueError(
                f"Special category types must be subset of data_type_categories. Invalid: {invalid}"
            )
        return v

    @model_validator(mode="after")
    def validate_rule_data_types(self) -> "PersonalDataRulesetData":
        """Validate all rule data_type values against master list."""
        valid_categories = set(self.data_type_categories)

        for rule in self.rules:
            if rule.data_type not in valid_categories:
                raise ValueError(
                    f"Rule '{rule.name}' has invalid data_type '{rule.data_type}'. Valid: {valid_categories}"
                )
        return self


class PersonalDataRuleset(AbstractRuleset[PersonalDataRule]):
    """Class-based personal data detection ruleset with logging support.

    This class provides structured access to personal data patterns
    with built-in logging capabilities for debugging and monitoring.
    """

    def __init__(self) -> None:
        """Initialise the personal data ruleset."""
        self._rules: tuple[PersonalDataRule, ...] | None = None
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
    def get_rules(self) -> tuple[PersonalDataRule, ...]:
        """Get the personal data rules.

        Returns:
            Immutable tuple of Rule objects containing all GDPR-compliant personal data patterns

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

            ruleset_data = PersonalDataRulesetData.model_validate(data)
            self._rules = tuple(ruleset_data.rules)
            logger.debug(f"Loaded {len(self._rules)} personal data ruleset data")

        return self._rules
