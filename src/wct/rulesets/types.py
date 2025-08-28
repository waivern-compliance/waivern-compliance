"""Pydantic-based types for structured rulesets with inheritance."""

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)


class RuleComplianceData(BaseModel):
    """Compliance information for a rule."""

    regulation: str = Field(
        ..., min_length=1, description="Regulation name (e.g., GDPR, CCPA)"
    )
    relevance: str = Field(
        ..., min_length=1, description="Specific relevance to this regulation"
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


class BaseRuleset[RuleType: BaseRule](BaseModel):
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


class ProcessingPurposeRule(BaseRule):
    """Processing purpose rule with category and risk information."""

    purpose_category: str = Field(description="Category of this processing purpose")


class ProcessingPurposesRulesetData(BaseRuleset[ProcessingPurposeRule]):
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


class PersonalDataRule(BaseRule):
    """Personal data rule with GDPR categories."""

    special_category: bool = Field(
        default=False,
        description="Whether this is GDPR Article 9 special category data",
    )


class PersonalDataRulesetData(BaseRuleset[PersonalDataRule]):
    """Personal data ruleset with GDPR Article 9 support."""

    # Ruleset-specific properties
    data_types: list[str] = Field(
        default_factory=list, description="Valid data types for this ruleset"
    )
    special_categories: list[str] = Field(
        default_factory=list,
        description="GDPR Article 9 special category types",
    )


class DataCollectionRule(BaseRule):
    """Data collection rule with collection type and source."""

    collection_type: str = Field(description="Type of data collection")
    data_source: str = Field(description="Source of the data")


class DataCollectionRulesetData(BaseRuleset[DataCollectionRule]):
    """Data collection ruleset data model."""


class ServiceIntegrationRule(BaseRule):
    """Service integration rule with service category and purpose."""

    service_category: str = Field(description="Category of service integration")
    purpose_category: str = Field(description="Purpose category for compliance")


class ServiceIntegrationsRulesetData(BaseRuleset[ServiceIntegrationRule]):
    """Service integrations ruleset data model."""
