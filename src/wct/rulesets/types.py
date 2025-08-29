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


class ProcessingPurposeRule(BaseRule):
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


class PersonalDataRule(BaseRule):
    """Personal data rule with GDPR categories."""

    data_type: str = Field(description="Type of personal data this rule detects")
    special_category: bool = Field(
        default=False,
        description="Whether this is GDPR Article 9 special category data",
    )


class PersonalDataRulesetData(RulesetData[PersonalDataRule]):
    """Personal data ruleset with GDPR Article 9 support."""

    # Ruleset-specific properties
    data_type_categories: list[str] = Field(
        min_length=1,
        description="Master list of valid personal data type categories based on GDPR requirements",
    )
    special_category_types: list[str] = Field(
        default_factory=list,
        description="Subset of data_type_categories that are GDPR Article 9 special category types",
    )

    @field_validator("special_category_types")
    @classmethod
    def validate_special_categories_subset(
        cls, v: list[str], info: ValidationInfo
    ) -> list[str]:
        """Ensure special_category_types is subset of data_type_categories."""
        data_type_categories = info.data.get("data_type_categories", [])
        invalid = [cat for cat in v if cat not in data_type_categories]
        if invalid:
            raise ValueError(
                f"Special category types must be subset of data_type_categories. Invalid: {invalid}"
            )
        return v

    @model_validator(mode="after")
    def validate_rule_data_types(self) -> "PersonalDataRulesetData":
        """Validate all rule data_type values against master list."""
        valid_categories = set(self.data_type_categories)

        for rule in self.rules:
            if rule.data_type not in valid_categories:
                raise ValueError(
                    f"Rule '{rule.name}' has invalid data_type '{rule.data_type}'. Valid: {valid_categories}"
                )
        return self


class DataCollectionRule(BaseRule):
    """Data collection rule with collection type and source."""

    collection_type: str = Field(description="Type of data collection")
    data_source: str = Field(description="Source of the data")


class DataCollectionRulesetData(RulesetData[DataCollectionRule]):
    """Data collection ruleset data model."""

    # Ruleset-specific properties
    collection_type_categories: list[str] = Field(
        min_length=1, description="Master list of valid data collection type categories"
    )
    data_source_categories: list[str] = Field(
        min_length=1, description="Master list of valid data source categories"
    )

    @model_validator(mode="after")
    def validate_rule_categories(self) -> "DataCollectionRulesetData":
        """Validate all rule collection_type and data_source values against master lists."""
        valid_collection_types = set(self.collection_type_categories)
        valid_data_sources = set(self.data_source_categories)

        for rule in self.rules:
            if rule.collection_type not in valid_collection_types:
                raise ValueError(
                    f"Rule '{rule.name}' has invalid collection_type '{rule.collection_type}'. Valid: {valid_collection_types}"
                )
            if rule.data_source not in valid_data_sources:
                raise ValueError(
                    f"Rule '{rule.name}' has invalid data_source '{rule.data_source}'. Valid: {valid_data_sources}"
                )
        return self


class ServiceIntegrationRule(BaseRule):
    """Service integration rule with service category and purpose."""

    service_category: str = Field(description="Category of service integration")
    purpose_category: str = Field(description="Purpose category for compliance")


class ServiceIntegrationsRulesetData(RulesetData[ServiceIntegrationRule]):
    """Service integrations ruleset data model."""

    # Ruleset-specific properties
    service_categories: list[str] = Field(
        min_length=1, description="Master list of valid service integration categories"
    )
    purpose_categories: list[str] = Field(
        min_length=1,
        description="Master list of valid purpose categories for service integrations",
    )

    @model_validator(mode="after")
    def validate_rule_categories(self) -> "ServiceIntegrationsRulesetData":
        """Validate all rule service_category and purpose_category values against master lists."""
        valid_service_categories = set(self.service_categories)
        valid_purpose_categories = set(self.purpose_categories)

        for rule in self.rules:
            if rule.service_category not in valid_service_categories:
                raise ValueError(
                    f"Rule '{rule.name}' has invalid service_category '{rule.service_category}'. Valid: {valid_service_categories}"
                )
            if rule.purpose_category not in valid_purpose_categories:
                raise ValueError(
                    f"Rule '{rule.name}' has invalid purpose_category '{rule.purpose_category}'. Valid: {valid_purpose_categories}"
                )
        return self
