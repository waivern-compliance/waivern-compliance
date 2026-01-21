"""Pydantic-based types for structured rulesets.

This module defines the rule type hierarchy:

- Rule: Base class with common properties (name, description)
- DetectionRule: Pattern-based rules for detecting content (used by analysers)
- ClassificationRule: Category mapping rules for regulatory interpretation (used by classifiers)

Note: Compliance framework association is determined by ruleset naming convention
and runbook configuration, not by rule properties. This keeps rules framework-agnostic
and gives runbook authors control over which rulesets apply to their compliance needs.
"""

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class Rule(BaseModel):
    """Base class for all compliance rules.

    Contains the common properties that every rule must have,
    regardless of whether it's a detection rule or classification rule.

    Attributes:
        name: Unique identifier for this rule
        description: Human-readable description of what this rule does

    Note:
        Risk assessment is intentionally excluded from this base class as it is
        a framework-specific concern. Each regulatory classifier should define
        its own risk model (e.g., GDPR uses special_category for risk).

    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, description="Unique name for this rule")
    description: str = Field(
        min_length=1,
        description="Human-readable description of what this rule does",
    )


class DetectionRule(Rule):
    """Pattern-based rule for detecting content in text.

    Used by analysers to detect personal data, processing purposes,
    data subjects, etc. by matching patterns against text content.

    Attributes:
        patterns: Tuple of word-boundary patterns to match (case-insensitive)
        value_patterns: Tuple of regex patterns for value-based detection

    """

    patterns: tuple[str, ...] = Field(
        default=(), description="Word-boundary patterns (case-insensitive matching)"
    )
    value_patterns: tuple[str, ...] = Field(
        default=(), description="Regex patterns for value-based detection"
    )

    @field_validator("patterns", "value_patterns")
    @classmethod
    def validate_patterns_not_empty_strings(
        cls, patterns: tuple[str, ...]
    ) -> tuple[str, ...]:
        """Validate that pattern tuples contain no empty strings."""
        if any(not pattern.strip() for pattern in patterns):
            raise ValueError("All patterns must be non-empty strings")
        return patterns

    @model_validator(mode="after")
    def validate_has_patterns(self) -> "DetectionRule":
        """Ensure at least one pattern type is specified."""
        if not self.patterns and not self.value_patterns:
            raise ValueError("Rule must have at least one pattern or value_pattern")
        return self


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
