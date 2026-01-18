"""GDPR personal data classification ruleset.

This module defines a ruleset for classifying personal data indicators
according to GDPR requirements. It maps generic personal data detection
categories to GDPR-specific data types and Article 9 special categories.
"""

from typing import ClassVar

from pydantic import Field, field_validator, model_validator
from waivern_core import RulesetData

from waivern_rulesets.core.base import YAMLRuleset
from waivern_rulesets.types import GDPRClassificationRule


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

    # Master list of valid privacy categories (for reporting/governance)
    # Note: These are NOT GDPR-defined terms - they're from legal team
    privacy_categories: list[str] = Field(
        min_length=1,
        description="Master list of valid privacy categories for reporting",
    )

    # Valid indicator categories that can be mapped
    indicator_categories: list[str] = Field(
        min_length=1,
        description="Master list of valid personal data indicator categories",
    )

    @model_validator(mode="after")
    def validate_rules(self) -> "GDPRPersonalDataClassificationRulesetData":
        """Validate all rules against master lists."""
        valid_privacy_cats = set(self.privacy_categories)
        valid_indicator_cats = set(self.indicator_categories)

        for rule in self.rules:
            # Validate privacy_category
            if rule.privacy_category not in valid_privacy_cats:
                msg = (
                    f"Rule '{rule.name}' has invalid privacy_category "
                    f"'{rule.privacy_category}'. Valid: {valid_privacy_cats}"
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
    YAMLRuleset[GDPRPersonalDataClassificationRule]
):
    """GDPR personal data classification ruleset.

    Provides classification mappings for personal data indicators,
    enriching generic findings with GDPR-specific information.
    """

    ruleset_name: ClassVar[str] = "gdpr_personal_data_classification"
    ruleset_version: ClassVar[str] = "1.0.0"
    _data_class: ClassVar[  # pyright: ignore[reportIncompatibleVariableOverride]
        type[GDPRPersonalDataClassificationRulesetData]
    ] = GDPRPersonalDataClassificationRulesetData
