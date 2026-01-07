"""GDPR personal data classification ruleset.

This module defines a ruleset for classifying personal data indicators
according to GDPR requirements. It maps generic personal data detection
categories to GDPR-specific data types and Article 9 special categories.
"""

import logging
from pathlib import Path
from typing import Final, override

import yaml
from pydantic import Field, ValidationInfo, field_validator, model_validator
from waivern_core import RulesetData

from waivern_rulesets.base import AbstractRuleset
from waivern_rulesets.types import GDPRClassificationRule

logger = logging.getLogger(__name__)

# Version constant for this ruleset and its data (private)
_RULESET_DATA_VERSION: Final[str] = "1.0.0"
_RULESET_NAME: Final[str] = "gdpr_personal_data_classification"


class GDPRPersonalDataClassificationRule(GDPRClassificationRule):
    """GDPR personal data classification rule.

    Maps personal data indicator categories to GDPR-specific classifications.
    Unlike detection rules, these rules don't have patterns - they map from
    indicator categories to GDPR data types.
    """

    indicator_categories: tuple[str, ...] = Field(
        min_length=1,
        description="Personal data indicator categories this rule classifies",
    )

    @field_validator("indicator_categories", mode="before")
    @classmethod
    def convert_list_to_tuple(cls, v: list[str] | tuple[str, ...]) -> tuple[str, ...]:
        """Convert list to tuple for immutability."""
        if isinstance(v, list):
            return tuple(v)
        return v


class GDPRPersonalDataClassificationRulesetData(
    RulesetData[GDPRPersonalDataClassificationRule]
):
    """GDPR personal data classification ruleset data with validation."""

    # Master list of valid GDPR data type categories
    gdpr_data_type_categories: list[str] = Field(
        min_length=1,
        description="Master list of valid GDPR data type categories",
    )

    # Subset that are GDPR Article 9 special categories
    special_category_types: list[str] = Field(
        default_factory=list,
        description="Subset of gdpr_data_type_categories that are Article 9 special categories",
    )

    # Valid indicator categories that can be mapped
    indicator_categories: list[str] = Field(
        min_length=1,
        description="Master list of valid personal data indicator categories",
    )

    @field_validator("special_category_types")
    @classmethod
    def validate_special_categories_subset(
        cls, v: list[str], info: ValidationInfo
    ) -> list[str]:
        """Ensure special_category_types is subset of gdpr_data_type_categories."""
        gdpr_data_type_categories = info.data.get("gdpr_data_type_categories", [])
        invalid = [cat for cat in v if cat not in gdpr_data_type_categories]
        if invalid:
            msg = (
                "special_category_types must be subset of gdpr_data_type_categories. "
                f"Invalid: {invalid}"
            )
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def validate_rules(self) -> "GDPRPersonalDataClassificationRulesetData":
        """Validate all rules against master lists."""
        valid_gdpr_types = set(self.gdpr_data_type_categories)
        valid_indicator_cats = set(self.indicator_categories)

        for rule in self.rules:
            # Validate gdpr_data_type
            if rule.gdpr_data_type not in valid_gdpr_types:
                msg = (
                    f"Rule '{rule.name}' has invalid gdpr_data_type "
                    f"'{rule.gdpr_data_type}'. Valid: {valid_gdpr_types}"
                )
                raise ValueError(msg)

            # Validate indicator_categories
            invalid_cats = [
                cat
                for cat in rule.indicator_categories
                if cat not in valid_indicator_cats
            ]
            if invalid_cats:
                msg = (
                    f"Rule '{rule.name}' has invalid indicator_categories: "
                    f"{invalid_cats}. Valid: {valid_indicator_cats}"
                )
                raise ValueError(msg)

        return self


class GDPRPersonalDataClassificationRuleset(
    AbstractRuleset[GDPRPersonalDataClassificationRule]
):
    """GDPR personal data classification ruleset.

    Provides structured access to GDPR classification mappings for
    personal data indicators. Used by the GDPRPersonalDataClassifier
    to enrich generic findings with GDPR-specific information.
    """

    def __init__(self) -> None:
        """Initialise the GDPR personal data classification ruleset."""
        self._rules: tuple[GDPRPersonalDataClassificationRule, ...] | None = None
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
    def get_rules(self) -> tuple[GDPRPersonalDataClassificationRule, ...]:
        """Get the GDPR classification rules.

        Returns:
            Immutable tuple of classification rules for GDPR personal data

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

            ruleset_data = GDPRPersonalDataClassificationRulesetData.model_validate(
                data
            )
            self._rules = tuple(ruleset_data.rules)
            logger.debug(f"Loaded {len(self._rules)} GDPR classification rules")

        return self._rules
