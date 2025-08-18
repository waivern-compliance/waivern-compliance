"""Types for processing purpose analyser."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Self

from wct.analysers.runners.types import LLMValidationConfig, PatternMatchingConfig


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
        default_factory=lambda: LLMValidationConfig(enable_llm_validation=False),
        description="LLM validation configuration (not yet implemented)",
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

    model_config = ConfigDict(extra="allow")


class ProcessingPurposeFindingModel(BaseModel):
    """Processing purpose finding structure."""

    purpose: str = Field(description="Processing purpose name")
    purpose_category: str = Field(
        default="OPERATIONAL", description="Category of the processing purpose"
    )
    risk_level: str = Field(description="Risk level of the finding")
    compliance_relevance: list[str] = Field(
        default_factory=lambda: ["GDPR"],
        description="Compliance frameworks this finding relates to",
    )
    matched_pattern: str = Field(description="Pattern that was matched")
    evidence: list[str] = Field(
        description="Evidence snippets that support the finding"
    )
    metadata: ProcessingPurposeFindingMetadata | None = Field(
        default=None, description="Additional metadata about the finding"
    )
