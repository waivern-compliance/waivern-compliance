"""Data subject indicator detection ruleset.

This module implements pattern-based data subject detection with confidence scoring
and context-aware pattern matching for identifying categories of data subjects.
"""

from typing import ClassVar, Literal

from pydantic import Field, model_validator
from waivern_core import DetectionRule, RulesetData

from waivern_rulesets.core.base import YAMLRuleset


class DataSubjectIndicatorRule(DetectionRule):
    """Data subject classification rule with confidence scoring.

    This rule type provides pattern-based data subject identification with
    configurable confidence weights for accurate classification.
    """

    subject_category: str = Field(
        description="Data subject category (e.g., employee, customer)"
    )
    indicator_type: Literal["primary", "secondary", "contextual"] = Field(
        description="Classification strength of this indicator"
    )
    confidence_weight: int = Field(
        ge=1, le=50, description="Confidence points awarded when this rule matches"
    )
    applicable_contexts: list[str] = Field(
        min_length=1,
        description="Data source contexts where this rule applies (e.g., database, filesystem, source_code)",
    )


class DataSubjectIndicatorRulesetData(RulesetData[DataSubjectIndicatorRule]):
    """Data subject ruleset data model with category management."""

    # Ruleset-specific properties
    subject_categories: list[str] = Field(
        min_length=1, description="Master list of valid data subject categories"
    )
    applicable_contexts: list[str] = Field(
        min_length=1, description="Master list of valid applicable contexts"
    )
    risk_increasing_modifiers: list[str] = Field(
        min_length=1,
        description="Risk-increasing modifiers (e.g., minor, vulnerable group)",
    )
    risk_decreasing_modifiers: list[str] = Field(
        min_length=1, description="Risk-decreasing modifiers (e.g., non-EU-resident)"
    )

    @model_validator(mode="after")
    def validate_rule_categories(self) -> "DataSubjectIndicatorRulesetData":
        """Validate all rule subject_category values against master list."""
        valid_categories = set(self.subject_categories)

        for rule in self.rules:
            if rule.subject_category not in valid_categories:
                raise ValueError(
                    f"Rule '{rule.name}' has invalid subject_category '{rule.subject_category}'. Valid: {valid_categories}"
                )
        return self

    @model_validator(mode="after")
    def validate_rule_contexts(self) -> "DataSubjectIndicatorRulesetData":
        """Validate all rule applicable_contexts values against master list."""
        valid_contexts = set(self.applicable_contexts)

        for rule in self.rules:
            invalid_contexts = set(rule.applicable_contexts) - valid_contexts
            if invalid_contexts:
                raise ValueError(
                    f"Rule '{rule.name}' has invalid applicable_contexts {sorted(invalid_contexts)}. Valid: {sorted(valid_contexts)}"
                )
        return self


class DataSubjectIndicatorRuleset(YAMLRuleset[DataSubjectIndicatorRule]):
    """Data subject indicator detection ruleset with confidence scoring.

    Identifies categories of individuals (e.g., employees, customers, patients)
    whose personal data is being processed.
    """

    ruleset_name: ClassVar[str] = "data_subject_indicator"
    ruleset_version: ClassVar[str] = "1.0.0"
    _data_class: ClassVar[  # pyright: ignore[reportIncompatibleVariableOverride]
        type[DataSubjectIndicatorRulesetData]
    ] = DataSubjectIndicatorRulesetData
