"""Schema data models for GDPR processing purpose classification findings."""

from typing import ClassVar, Literal, override

from pydantic import BaseModel, Field
from waivern_core.schemas import (
    BaseAnalysisOutputMetadata,
    BaseFindingEvidence,
    BaseFindingMetadata,
    BaseFindingModel,
    BaseSchemaOutput,
)


class GDPRProcessingPurposeFindingMetadata(BaseFindingMetadata):
    """Metadata for GDPR processing purpose classification findings.

    Extends BaseFindingMetadata which provides:
    - source: str - Source file or location where the data was found
    - context: dict[str, object] - Extensible context for pipeline metadata
    """

    pass


class GDPRProcessingPurposeFindingModel(
    BaseFindingModel[GDPRProcessingPurposeFindingMetadata]
):
    """GDPR processing purpose classification finding structure.

    Represents a processing purpose indicator that has been enriched with
    GDPR-specific classification information. Sensitive purposes (e.g., AI/ML,
    analytics, marketing) may require additional considerations such as
    explicit consent or DPIA under GDPR.

    Inherits from BaseFindingModel[GDPRProcessingPurposeFindingMetadata] which provides:
    - id: str - Unique identifier (auto-generated UUID)
    - evidence: list[BaseFindingEvidence] - Evidence items with content
    - matched_patterns: list[PatternMatchDetail] - Patterns that matched
    - metadata: GDPRProcessingPurposeFindingMetadata - Required metadata with source
    """

    # Original indicator data (propagated)
    processing_purpose: str = Field(
        description="Processing purpose name from indicator (e.g., 'Analytics', 'Payment Processing')"
    )

    # GDPR classification (from ruleset mapping)
    purpose_category: str = Field(
        description="Normalised GDPR purpose category (e.g., 'analytics', 'operational')"
    )
    article_references: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Relevant GDPR article references (e.g., 'Article 6(1)(a)', 'Article 22')",
    )
    typical_lawful_bases: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Typical GDPR Article 6 lawful bases for this processing purpose",
    )

    # Risk/sensitivity indicators
    sensitive_purpose: bool = Field(
        default=False,
        description="Whether this purpose is privacy-sensitive (AI/ML, analytics, marketing)",
    )
    dpia_recommendation: Literal["required", "recommended", "not_required"] = Field(
        default="not_required",
        description="DPIA recommendation level for this purpose",
    )

    @override
    def __str__(self) -> str:
        """Human-readable representation for logging and debugging."""
        sensitive = " [SENSITIVE]" if self.sensitive_purpose else ""
        return f"{self.processing_purpose} → {self.purpose_category}{sensitive}"


class GDPRProcessingPurposeSummary(BaseModel):
    """Summary statistics for GDPR processing purpose classification findings."""

    total_findings: int = Field(
        ge=0, description="Total number of classified processing purpose findings"
    )
    purpose_categories: dict[str, int] = Field(
        default_factory=dict,
        description="Count of findings per GDPR purpose category",
    )
    sensitive_purposes_count: int = Field(
        ge=0,
        description="Number of findings with sensitive purposes",
    )
    dpia_required_count: int = Field(
        ge=0,
        description="Number of findings where DPIA is required",
    )


class GDPRProcessingPurposeFindingOutput(BaseSchemaOutput):
    """Complete output structure for gdpr_processing_purpose schema.

    This model represents the full wire format for GDPR processing purpose
    classification results, including findings enriched with GDPR-specific
    information, summary statistics, and analysis metadata.
    """

    __schema_version__: ClassVar[str] = "1.0.0"

    findings: list[GDPRProcessingPurposeFindingModel] = Field(
        description="List of processing purpose findings with GDPR classification"
    )
    summary: GDPRProcessingPurposeSummary = Field(
        description="Summary statistics of the GDPR classification analysis"
    )
    analysis_metadata: BaseAnalysisOutputMetadata = Field(
        description="Metadata about the classification process"
    )


__all__ = [
    "BaseFindingEvidence",
    "GDPRProcessingPurposeFindingMetadata",
    "GDPRProcessingPurposeFindingModel",
    "GDPRProcessingPurposeFindingOutput",
    "GDPRProcessingPurposeSummary",
]
