"""Types for processing purpose analyser."""

from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field
from waivern_core.schemas import (
    BaseFindingModel,
)

from waivern_community.analysers.types import (
    LLMValidationConfig,
    PatternMatchingConfig,
)


class ProcessingPurposeAnalyserConfig(BaseModel):
    """Configuration for ProcessingPurposeAnalyser.

    Groups related configuration parameters to reduce constructor complexity.
    Uses Pydantic for validation and default values.
    """

    pattern_matching: PatternMatchingConfig = Field(
        default_factory=lambda: PatternMatchingConfig(ruleset="processing_purposes"),
        description="Pattern matching configuration",
    )
    llm_validation: LLMValidationConfig = Field(
        default_factory=lambda: LLMValidationConfig(enable_llm_validation=True),
        description="LLM validation configuration for filtering false positives",
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


class ProcessingPurposeFindingMetadata(BaseModel):
    """Metadata for processing purpose findings."""

    source: str = Field(description="Source file or location where the data was found")

    model_config = ConfigDict(extra="forbid")


class ProcessingPurposeFindingModel(BaseFindingModel):
    """Processing purpose finding structure."""

    purpose: str = Field(description="Processing purpose name")
    purpose_category: str = Field(
        default="", description="Category of the processing purpose"
    )
    metadata: ProcessingPurposeFindingMetadata | None = Field(
        default=None, description="Additional metadata about the finding"
    )
    service_category: str | None = Field(
        default=None,
        description="Service category from ServiceIntegrationRule (when applicable)",
    )
    collection_type: str | None = Field(
        default=None,
        description="Collection type from DataCollectionRule (when applicable)",
    )
    data_source: str | None = Field(
        default=None,
        description="Data source from DataCollectionRule (when applicable)",
    )
