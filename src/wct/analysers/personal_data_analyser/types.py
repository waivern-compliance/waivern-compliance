"""Data models for personal data analysis analyser."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing_extensions import Self

from wct.analysers.runners.types import (
    LLMValidationConfig,
    PatternMatchingConfig,
)


class PersonalDataAnalyserConfig(BaseModel):
    """Configuration for PersonalDataAnalyser with nested runner configs.

    This provides clear separation of concerns where each runner has its own
    configuration section in the runbook properties.
    """

    pattern_matching: PatternMatchingConfig = Field(
        default_factory=lambda: PatternMatchingConfig(ruleset="personal_data"),
        description="Pattern matching configuration for personal data detection",
    )
    llm_validation: LLMValidationConfig = Field(
        default_factory=lambda: LLMValidationConfig(enable_llm_validation=True),
        description="LLM validation configuration for filtering false positives",
    )

    @classmethod
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create configuration from runbook properties with nested structure.

        Args:
            properties: Raw properties from runbook with nested configuration

        Returns:
            Validated configuration object

        """
        return cls.model_validate(properties)


class PersonalDataFindingMetadata(BaseModel):
    """Metadata for personal data findings that matches the JSON schema."""

    source: str = Field(description="Source file or location where the data was found")

    model_config = ConfigDict(extra="allow")


class PersonalDataFindingModel(BaseModel):
    """Personal data finding structure."""

    type: str = Field(
        description="Type of personal data found (e.g., 'email', 'phone_number')"
    )
    risk_level: str = Field(description="Risk assessment level (low, medium, high)")
    special_category: str | None = Field(
        default=None, description="GDPR special category indicator (Y/N)"
    )
    matched_pattern: str = Field(
        description="Specific pattern that matched in the content"
    )
    evidence: list[str] | None = Field(
        default=None,
        description="Evidence snippets from content that matches this finding",
    )
    metadata: PersonalDataFindingMetadata | None = Field(
        default=None, description="Additional metadata from the original data source"
    )

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, v: str) -> str:
        """Validate risk level values."""
        allowed = ["low", "medium", "high"]
        if v not in allowed:
            raise ValueError(f"risk_level must be one of {allowed}, got: {v}")
        return v
