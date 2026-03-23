"""Schema data models for GDPR data collection classification findings."""

from typing import ClassVar, Literal, override

from pydantic import BaseModel, Field
from waivern_core.schemas import (
    BaseAnalysisOutputMetadata,
    BaseFindingMetadata,
    BaseFindingModel,
    BaseSchemaOutput,
)


class GDPRDataCollectionFindingMetadata(BaseFindingMetadata):
    """Metadata for GDPR data collection classification findings.

    Extends BaseFindingMetadata which provides:
    - source: str - Source file or location where the data was found
    - context: dict[str, object] - Extensible context for pipeline metadata
    """

    pass


class GDPRDataCollectionFindingModel(
    BaseFindingModel[GDPRDataCollectionFindingMetadata]
):
    """GDPR data collection classification finding structure.

    Represents a data collection indicator that has been enriched with
    GDPR-specific classification information. Contains both the original
    indicator fields and the GDPR assessment.

    Inherits from BaseFindingModel[GDPRDataCollectionFindingMetadata] which provides:
    - id: str - Unique identifier (auto-generated UUID)
    - evidence: list[BaseFindingEvidence] - Evidence items with content
    - matched_patterns: list[PatternMatchDetail] - Patterns that matched
    - metadata: GDPRDataCollectionFindingMetadata - Required metadata with source
    - require_review: bool | None - Whether this finding requires human review
    """

    # Original indicator data (propagated)
    collection_type: str = Field(
        description="Collection type slug from indicator (e.g., 'form_data', 'cookies')"
    )
    data_source: str = Field(
        description="Data source from indicator (e.g., 'http_post', 'mysql')"
    )

    # GDPR classification (from ruleset mapping)
    gdpr_purpose_category: str = Field(
        description="GDPR purpose category from classification (e.g., 'context_dependent')"
    )
    article_references: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Relevant GDPR article references (e.g., 'Article 5', 'Article 6')",
    )
    typical_lawful_bases: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Typical GDPR Article 6 lawful bases for this data collection mechanism",
    )

    # Risk/sensitivity indicators
    sensitive_purpose: bool = Field(
        default=False,
        description="Whether this data collection mechanism's purpose is privacy-sensitive",
    )
    dpia_recommendation: Literal["required", "recommended", "not_required"] = Field(
        default="not_required",
        description="DPIA recommendation level for this data collection mechanism",
    )

    @override
    def __str__(self) -> str:
        """Human-readable representation for logging and debugging."""
        sensitive = " [SENSITIVE]" if self.sensitive_purpose else ""
        return f"{self.collection_type} → {self.gdpr_purpose_category}{sensitive}"


class GDPRDataCollectionSummary(BaseModel):
    """Summary statistics for GDPR data collection classification findings."""

    total_findings: int = Field(
        ge=0, description="Total number of classified data collection findings"
    )
    gdpr_purpose_categories: dict[str, int] = Field(
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
    requires_review_count: int = Field(
        ge=0,
        description="Number of findings that require human review",
    )


class GDPRDataCollectionFindingOutput(BaseSchemaOutput):
    """Complete output structure for gdpr_data_collection schema.

    This model represents the full wire format for GDPR data collection
    classification results, including findings enriched with GDPR-specific
    information, summary statistics, and analysis metadata.
    """

    __schema_version__: ClassVar[str] = "1.0.0"

    findings: list[GDPRDataCollectionFindingModel] = Field(
        description="List of data collection findings with GDPR classification"
    )
    summary: GDPRDataCollectionSummary = Field(
        description="Summary statistics of the GDPR classification analysis"
    )
    analysis_metadata: BaseAnalysisOutputMetadata = Field(
        description="Metadata about the classification process"
    )


__all__ = [
    "GDPRDataCollectionFindingMetadata",
    "GDPRDataCollectionFindingModel",
    "GDPRDataCollectionFindingOutput",
    "GDPRDataCollectionSummary",
]
