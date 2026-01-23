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

    A simple detection rule for identifying processing purposes.
    Inherits name, description, patterns, and value_patterns from DetectionRule.
    """

    pass


class ProcessingPurposesRulesetData(RulesetData[ProcessingPurposeRule]):
    """Processing purposes ruleset data model with validation."""

    purposes: list[str] = Field(
        min_length=1, description="Master list of valid processing purpose names"
    )

    @model_validator(mode="after")
    def validate_rule_names_in_purposes(self) -> "ProcessingPurposesRulesetData":
        """Validate all rule names exist in the purposes list."""
        valid_purposes = set(self.purposes)

        for rule in self.rules:
            if rule.name not in valid_purposes:
                raise ValueError(
                    f"Rule '{rule.name}' is not in purposes list. "
                    f"Add it to purposes or remove the rule."
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
