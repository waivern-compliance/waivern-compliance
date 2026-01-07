"""Pydantic-based types for structured rulesets.

This module defines the rule type hierarchy:

- Rule: Base class with common properties (name, description, risk_level)
- DetectionRule: Pattern-based rules for detecting content (used by analysers)
- ClassificationRule: Category mapping rules for regulatory interpretation (used by classifiers)

Note: Compliance framework association is determined by ruleset naming convention
and runbook configuration, not by rule properties. This keeps rules framework-agnostic
and gives runbook authors control over which rulesets apply to their compliance needs.
"""

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class Rule(BaseModel):
    """Base class for all compliance rules.

    Contains the common properties that every rule must have,
    regardless of whether it's a detection rule or classification rule.

    Attributes:
        name: Unique identifier for this rule
        description: Human-readable description of what this rule does
        risk_level: Risk assessment (low, medium, high)

    Note:
        Compliance framework association is implicit via ruleset naming
        (e.g., 'gdpr_personal_data_classification') rather than explicit
        per-rule properties. This keeps detection rules framework-agnostic.

    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, description="Unique name for this rule")
    description: str = Field(
        min_length=1,
        description="Human-readable description of what this rule does",
    )
    risk_level: Literal["low", "medium", "high"] = Field(
        description="Risk level assessment"
    )


class DetectionRule(Rule):
    """Pattern-based rule for detecting content in text.

    Used by analysers to detect personal data, processing purposes,
    data subjects, etc. by matching patterns against text content.

    Attributes:
        patterns: Tuple of patterns to match (case-insensitive word boundary matching)

    """

    patterns: tuple[str, ...] = Field(
        min_length=1, description="Tuple of patterns to match"
    )

    @field_validator("patterns")
    @classmethod
    def validate_patterns_not_empty(cls, patterns: tuple[str, ...]) -> tuple[str, ...]:
        """Validate that patterns contains at least one non-empty pattern."""
        if not patterns:
            raise ValueError("Rule must contain at least one pattern")
        if any(not pattern.strip() for pattern in patterns):
            raise ValueError("All patterns must be non-empty strings")
        return patterns


class ClassificationRule(Rule):
    """Base class for rules that classify findings into regulatory categories.

    Used by classifiers to map generic detection findings to framework-specific
    classifications (e.g., GDPR data types, Article 9 special categories).

    Unlike DetectionRule, this does not have patterns - it maps from
    detection categories to regulatory interpretations.

    Subclasses add framework-specific fields like:
        - gdpr_data_type: GDPR data type classification
        - special_category: Whether this is Article 9 special category data
        - article_references: Relevant GDPR articles

    """

    pass


class RulesetData[RuleType: Rule](BaseModel):
    """Base ruleset data class for YAML parsing.

    Generic over RuleType which can be Rule, DetectionRule, ClassificationRule,
    or any subclass thereof.
    """

    name: str = Field(min_length=1, description="Canonical name of the ruleset")
    version: str = Field(
        pattern=r"^\d+\.\d+\.\d+$", description='Semantic version (e.g., "1.0.0")'
    )
    description: str = Field(
        min_length=1, description="Description of what this ruleset does"
    )
    rules: list[RuleType] = Field(
        min_length=1, description="List of rules in this ruleset"
    )

    @field_validator("rules")
    @classmethod
    def validate_unique_rule_names(cls, rules: list[RuleType]) -> list[RuleType]:
        """Validate that rule names are unique within the ruleset."""
        names = [rule.name for rule in rules]
        duplicates = [name for name in names if names.count(name) > 1]
        if duplicates:
            raise ValueError(f"Duplicate rule names found: {duplicates}")
        return rules
