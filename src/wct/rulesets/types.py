"""Pydantic-based types for structured rulesets."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RuleComplianceData(BaseModel):
    """Compliance information for a rule."""

    regulation: str = Field(
        ..., min_length=1, description="Regulation name (e.g., GDPR, CCPA)"
    )
    relevance: str = Field(
        ..., min_length=1, description="Specific relevance to this regulation"
    )


class RuleData(BaseModel):
    """Type definition for rule pattern data in PATTERNS dictionaries."""

    description: str = Field(
        ..., min_length=1, description="Human-readable description"
    )
    patterns: tuple[str, ...] = Field(
        ..., min_length=1, description="Tuple of patterns to match"
    )
    risk_level: Literal["low", "medium", "high"] = Field(
        ..., description="Risk level assessment"
    )
    compliance: list[RuleComplianceData] = Field(
        default_factory=list, description="Compliance information"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Flexible metadata dictionary"
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


class Rule(BaseModel):
    """Immutable structured rule for pattern matching.

    A rule represents a category of patterns to match, with associated metadata.
    All rules have a risk_level as this is universal across rulesets.
    The metadata property can hold any additional ruleset-specific information.

    This provides a type-safe structure while maintaining flexibility through the metadata dict.
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., min_length=1, description="Unique name for this rule")
    description: str = Field(
        ...,
        min_length=1,
        description="Human-readable description of what this rule detects",
    )
    patterns: tuple[str, ...] = Field(
        ..., min_length=1, description="Tuple of patterns to match"
    )
    risk_level: Literal["low", "medium", "high"] = Field(
        ..., description="Risk level assessment"
    )
    compliance: list[RuleComplianceData] = Field(
        default_factory=list, description="Compliance information"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Flexible metadata dictionary"
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


class RulesetData(BaseModel):
    """Complete ruleset definition loaded from external sources like YAML."""

    name: str = Field(..., min_length=1, description="Canonical name of the ruleset")
    version: str = Field(
        ..., pattern=r"^\d+\.\d+\.\d+$", description='Semantic version (e.g., "1.0.0")'
    )
    description: str = Field(
        ..., min_length=1, description="Description of what this ruleset detects"
    )
    rules: dict[str, RuleData] = Field(
        ..., min_length=1, description="Dictionary of rule name to rule data"
    )

    @field_validator("rules")
    @classmethod
    def validate_rules_not_empty(
        cls, rules: dict[str, RuleData]
    ) -> dict[str, RuleData]:
        """Validate that the ruleset contains at least one rule."""
        if not rules:
            raise ValueError("Ruleset must contain at least one rule")
        return rules

    def to_rules(self) -> tuple[Rule, ...]:
        """Convert this ruleset definition to a tuple of Rule objects.

        Returns:
            Tuple of Rule objects created from the ruleset definition

        """
        rule_objects: list[Rule] = []
        for rule_name, rule_data in self.rules.items():
            rule_objects.append(
                Rule(
                    name=rule_name,
                    description=rule_data.description,
                    patterns=rule_data.patterns,
                    risk_level=rule_data.risk_level,
                    compliance=rule_data.compliance,
                    metadata=rule_data.metadata,
                )
            )
        return tuple(rule_objects)
