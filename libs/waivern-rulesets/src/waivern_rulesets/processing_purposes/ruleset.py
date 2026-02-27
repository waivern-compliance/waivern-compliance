"""Known processing purposes to search for during analysis.

This ruleset contains processing purpose patterns for detecting data processing
activities in source code and documents.
"""

from typing import ClassVar

from pydantic import Field, model_validator
from waivern_core import DetectionRule, RulesetData

from waivern_rulesets.core.base import YAMLRuleset


class ProcessingPurposeRule(DetectionRule):
    """Processing purpose detection rule.

    Inherits name, description, patterns, and value_patterns from DetectionRule.
    The `purpose` slug is the canonical machine-readable identifier output in
    findings — distinct from the human-readable `name` field.
    """

    purpose: str = Field(
        description="Snake_case slug used as the canonical purpose identifier in findings "
        "(e.g. 'user_identity_login'). Distinct from the human-readable rule name.",
    )


class ProcessingPurposesRulesetData(RulesetData[ProcessingPurposeRule]):
    """Processing purposes ruleset data model with validation."""

    purposes: list[str] = Field(
        min_length=1, description="Master list of valid processing purpose names"
    )
    purpose_slugs: list[str] = Field(
        min_length=1, description="Master list of valid purpose slugs (snake_case)"
    )

    @model_validator(mode="after")
    def validate_rules(self) -> "ProcessingPurposesRulesetData":
        """Validate all rule names and purpose slugs against master lists."""
        valid_purposes = set(self.purposes)
        valid_slugs = set(self.purpose_slugs)

        for rule in self.rules:
            if rule.name not in valid_purposes:
                raise ValueError(
                    f"Rule '{rule.name}' is not in purposes list. "
                    f"Add it to purposes or remove the rule."
                )
            if rule.purpose not in valid_slugs:
                raise ValueError(
                    f"Rule '{rule.name}' has purpose slug '{rule.purpose}' "
                    f"not in purpose_slugs list. Add it to purpose_slugs or fix the slug."
                )
        return self


class ProcessingPurposesRuleset(YAMLRuleset[ProcessingPurposeRule]):
    """Processing purposes detection ruleset.

    Identifies business activities and data use intentions in source code
    and documents.
    """

    ruleset_name: ClassVar[str] = "processing_purposes"
    ruleset_version: ClassVar[str] = "1.0.0"
    _data_class: ClassVar[  # pyright: ignore[reportIncompatibleVariableOverride]
        type[ProcessingPurposesRulesetData]
    ] = ProcessingPurposesRulesetData
