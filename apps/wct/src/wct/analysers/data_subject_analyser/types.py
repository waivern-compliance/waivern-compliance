"""Types for data subject analyser."""

from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field

from wct.analysers.types import (
    LLMValidationConfig,
    PatternMatchingConfig,
)
from wct.schemas.types import BaseFindingModel


class DataSubjectAnalyserConfig(BaseModel):
    """Configuration for DataSubjectAnalyser.

    Groups related configuration parameters to reduce constructor complexity.
    Uses Pydantic for validation and default values.
    """

    pattern_matching: PatternMatchingConfig = Field(
        default_factory=lambda: PatternMatchingConfig(ruleset="data_subjects"),
        description="Pattern matching configuration",
    )
    llm_validation: LLMValidationConfig = Field(
        default_factory=lambda: LLMValidationConfig(enable_llm_validation=False),
        description="LLM validation configuration for improving classification accuracy",
    )

    @classmethod
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create configuration from runbook properties.

        Args:
            properties: Raw properties from runbook configuration

        Returns:
            Validated configuration object

        """
        return cls.model_validate(properties)


class DataSubjectFindingMetadata(BaseModel):
    """Metadata for data subject findings."""

    source: str = Field(description="Source file or location where the data was found")

    model_config = ConfigDict(extra="forbid")


class DataSubjectFindingModel(BaseFindingModel):
    """Data subject finding structure."""

    primary_category: str = Field(description="Primary data subject category")
    confidence_score: int = Field(
        ge=0, le=100, description="Confidence score for the classification (0-100)"
    )
    modifiers: list[str] = Field(
        default_factory=list,
        description="Cross-category regulatory modifiers from ruleset",
    )
    metadata: DataSubjectFindingMetadata | None = Field(
        default=None, description="Additional metadata about the finding"
    )
