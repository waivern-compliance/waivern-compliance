"""Types for processing purpose analyser."""

from pydantic import BaseModel, ConfigDict, Field


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
