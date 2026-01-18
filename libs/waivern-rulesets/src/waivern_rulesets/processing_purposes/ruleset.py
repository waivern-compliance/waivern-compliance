"""Known processing purposes to search for during analysis.

This ruleset contains processing purpose patterns for GDPR compliance analysis.
Version 1.0.0 has separated service integration patterns into dedicated service_integrations ruleset.
"""

from typing import ClassVar

from pydantic import Field, ValidationInfo, field_validator, model_validator
from waivern_core import DetectionRule, RulesetData

from waivern_rulesets.core.base import YAMLRuleset


class ProcessingPurposeRule(DetectionRule):
    """Processing purpose rule with category and risk information."""

    purpose_category: str = Field(description="Category of this processing purpose")


class ProcessingPurposesRulesetData(RulesetData[ProcessingPurposeRule]):
    """Processing purposes ruleset data model with category management."""

    # Ruleset-specific properties
    purpose_categories: list[str] = Field(
        min_length=1, description="Master list of valid purpose categories"
    )
    sensitive_categories: list[str] = Field(
        default_factory=list,
        description="Subset of purpose_categories considered privacy-sensitive",
    )

    @field_validator("sensitive_categories")
    @classmethod
    def validate_sensitive_categories_subset(
        cls, v: list[str], info: ValidationInfo
    ) -> list[str]:
        """Ensure sensitive_categories is subset of purpose_categories."""
        purpose_categories = info.data.get("purpose_categories", [])
        invalid = [cat for cat in v if cat not in purpose_categories]
        if invalid:
            raise ValueError(
                f"Sensitive categories must be subset of purpose_categories. Invalid: {invalid}"
            )
        return v

    @model_validator(mode="after")
    def validate_rule_categories(self) -> "ProcessingPurposesRulesetData":
        """Validate all rule purpose_categories against master list."""
        purpose_categories = set(self.purpose_categories)

        for rule in self.rules:
            if rule.purpose_category not in purpose_categories:
                raise ValueError(
                    f"Rule '{rule.name}' has invalid purpose_category '{rule.purpose_category}'. Valid: {purpose_categories}"
                )
        return self


class ProcessingPurposesRuleset(YAMLRuleset[ProcessingPurposeRule]):
    """Processing purposes detection ruleset.

    Identifies business activities and data use intentions for privacy compliance,
    consent management, and understanding data processing activities.
    """

    ruleset_name: ClassVar[str] = "processing_purposes"
    ruleset_version: ClassVar[str] = "1.0.0"
    _data_class: ClassVar[  # pyright: ignore[reportIncompatibleVariableOverride]
        type[ProcessingPurposesRulesetData]
    ] = ProcessingPurposesRulesetData
