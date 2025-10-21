"""Data models for personal data analysis analyser."""

from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field
from waivern_analysers_shared.types import (
    LLMValidationConfig,
    PatternMatchingConfig,
)
from waivern_core.schemas import (
    BaseFindingModel,
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

    model_config = ConfigDict(extra="forbid")


class PersonalDataFindingModel(BaseFindingModel):
    """Personal data finding structure."""

    type: str = Field(
        description="Type of personal data found (e.g., 'email', 'phone_number')"
    )
    data_type: str = Field(
        description="Categorical data type identifier from GDPR classification (e.g., 'basic_profile', 'health_data')"
    )
    special_category: bool = Field(
        default=False,
        description="Whether this is GDPR Article 9 special category data",
    )
    metadata: PersonalDataFindingMetadata | None = Field(
        default=None, description="Additional metadata from the original data source"
    )
