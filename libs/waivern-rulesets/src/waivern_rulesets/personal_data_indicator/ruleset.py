"""Personal data indicator detection ruleset.

This module defines a ruleset for detecting personal data patterns.
It provides framework-agnostic indicators that can be consumed by
regulatory classifiers (e.g., GDPR, CCPA) for framework-specific enrichment.
"""

from typing import ClassVar

from pydantic import Field, model_validator
from waivern_core import DetectionRule, RulesetData

from waivern_rulesets.core.base import YAMLRuleset


class PersonalDataIndicatorRule(DetectionRule):
    """Personal data indicator detection rule.

    This is a framework-agnostic detection rule. Regulatory classification
    (e.g., GDPR Article 9 special categories) is performed by downstream
    classifiers, not by this ruleset.
    """

    category: str = Field(
        description="Category of personal data this rule detects (e.g., 'basic_profile', 'health_data')"
    )


class PersonalDataIndicatorRulesetData(RulesetData[PersonalDataIndicatorRule]):
    """Personal data indicator ruleset data structure."""

    # Ruleset-specific properties
    categories: list[str] = Field(
        min_length=1,
        description="Master list of valid personal data indicator categories",
    )

    @model_validator(mode="after")
    def validate_rule_categories(self) -> "PersonalDataIndicatorRulesetData":
        """Validate all rule category values against master list."""
        valid_categories = set(self.categories)

        for rule in self.rules:
            if rule.category not in valid_categories:
                raise ValueError(
                    f"Rule '{rule.name}' has invalid category '{rule.category}'. Valid: {valid_categories}"
                )
        return self


class PersonalDataIndicatorRuleset(YAMLRuleset[PersonalDataIndicatorRule]):
    """Personal data indicator detection ruleset.

    Provides structured access to personal data patterns for compliance analysis.
    """

    ruleset_name: ClassVar[str] = "personal_data_indicator"
    ruleset_version: ClassVar[str] = "1.0.0"
    _data_class: ClassVar[  # pyright: ignore[reportIncompatibleVariableOverride]
        type[PersonalDataIndicatorRulesetData]
    ] = PersonalDataIndicatorRulesetData
