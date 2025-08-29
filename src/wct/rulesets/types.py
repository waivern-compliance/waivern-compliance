"""Pydantic-based types for structured rulesets with inheritance."""

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class RuleComplianceData(BaseModel):
    """Compliance information for a rule."""

    regulation: str = Field(
        min_length=1, description="Regulation name (e.g., GDPR, CCPA)"
    )
    relevance: str = Field(
        min_length=1, description="Specific relevance to this regulation"
    )


class BaseRule(BaseModel):
    """Base rule class with minimal guaranteed properties."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, description="Unique name for this rule")
    description: str = Field(
        min_length=1,
        description="Human-readable description of what this rule detects",
    )
    patterns: tuple[str, ...] = Field(
        min_length=1, description="Tuple of patterns to match"
    )
    risk_level: Literal["low", "medium", "high"] = Field(
        description="Risk level assessment"
    )
    compliance: list[RuleComplianceData] = Field(
        default_factory=list, description="Compliance information"
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


class RulesetData[RuleType: BaseRule](BaseModel):
    """Base ruleset class with minimal guaranteed properties."""

    name: str = Field(min_length=1, description="Canonical name of the ruleset")
    version: str = Field(
        pattern=r"^\d+\.\d+\.\d+$", description='Semantic version (e.g., "1.0.0")'
    )
    description: str = Field(
        min_length=1, description="Description of what this ruleset detects"
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
