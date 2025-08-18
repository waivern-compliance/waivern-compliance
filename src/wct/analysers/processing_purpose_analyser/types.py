"""Types for processing purpose analyser."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing_extensions import Self


class ProcessingPurposeAnalyserConfig(BaseModel):
    """Configuration for ProcessingPurposeAnalyser.

    Groups related configuration parameters to reduce constructor complexity.
    Uses Pydantic for validation and default values.
    """

    ruleset_name: str = Field(
        default="processing_purposes",
        description="Name of the ruleset to use for pattern matching",
    )
    evidence_context_size: str = Field(
        default="medium", description="Size of evidence context for analysis"
    )

    @field_validator("evidence_context_size")
    @classmethod
    def validate_evidence_context_size(cls, v: str) -> str:
        """Validate evidence context size values."""
        allowed = ["small", "medium", "large"]
        if v not in allowed:
            raise ValueError(
                f"evidence_context_size must be one of {allowed}, got: {v}"
            )
        return v

    enable_llm_validation: bool = Field(
        default=True, description="Whether to enable LLM validation"
    )
    llm_batch_size: int = Field(
        default=30, ge=1, le=200, description="Batch size for LLM processing"
    )
    confidence_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for findings",
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
    confidence: float = Field(description="Confidence score for the finding")
    evidence: list[str] = Field(
        description="Evidence snippets that support the finding"
    )
    metadata: ProcessingPurposeFindingMetadata | None = Field(
        default=None, description="Additional metadata about the finding"
    )
