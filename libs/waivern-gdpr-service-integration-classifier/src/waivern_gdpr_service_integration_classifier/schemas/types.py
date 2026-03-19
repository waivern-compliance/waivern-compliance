"""Schema data models for GDPR service integration classification findings."""

from typing import ClassVar, Literal, override

from pydantic import BaseModel, Field
from waivern_core.schemas import (
    BaseAnalysisOutputMetadata,
    BaseFindingEvidence,
    BaseFindingMetadata,
    BaseFindingModel,
    BaseSchemaOutput,
)


class GDPRServiceIntegrationFindingMetadata(BaseFindingMetadata):
    """Metadata for GDPR service integration classification findings.

    Extends BaseFindingMetadata which provides:
    - source: str - Source file or location where the data was found
    - context: dict[str, object] - Extensible context for pipeline metadata
    """

    pass


class GDPRServiceIntegrationFindingModel(
    BaseFindingModel[GDPRServiceIntegrationFindingMetadata]
):
    """GDPR service integration classification finding structure.

    Represents a service integration indicator that has been enriched with
    GDPR-specific classification information. Contains both the original
    indicator fields and the GDPR assessment.

    Inherits from BaseFindingModel[GDPRServiceIntegrationFindingMetadata] which provides:
    - id: str - Unique identifier (auto-generated UUID)
    - evidence: list[BaseFindingEvidence] - Evidence items with content
    - matched_patterns: list[PatternMatchDetail] - Patterns that matched
    - metadata: GDPRServiceIntegrationFindingMetadata - Required metadata with source
    - require_review: bool | None - Whether this finding requires human review
    """

    # Original indicator data (propagated)
    service_category: str = Field(
        description="Service category slug from indicator (e.g., 'cloud_infrastructure', 'communication')"
    )
    service_integration_purpose: str = Field(
        description="Purpose category from the service integration detection rule (e.g., 'operational', 'analytics')"
    )

    # GDPR classification (from ruleset mapping)
    gdpr_purpose_category: str = Field(
        description="GDPR purpose category from classification (e.g., 'operational', 'context_dependent')"
    )
    article_references: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Relevant GDPR article references (e.g., 'Article 28', 'Article 32')",
    )
    typical_lawful_bases: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Typical GDPR Article 6 lawful bases for this service integration",
    )

    # Risk/sensitivity indicators
    sensitive_purpose: bool = Field(
        default=False,
        description="Whether this service integration's purpose is privacy-sensitive",
    )
    dpia_recommendation: Literal["required", "recommended", "not_required"] = Field(
        default="not_required",
        description="DPIA recommendation level for this service integration",
    )

    @override
    def __str__(self) -> str:
        """Human-readable representation for logging and debugging."""
        sensitive = " [SENSITIVE]" if self.sensitive_purpose else ""
        return f"{self.service_category} → {self.gdpr_purpose_category}{sensitive}"


class GDPRServiceIntegrationSummary(BaseModel):
    """Summary statistics for GDPR service integration classification findings."""

    total_findings: int = Field(
        ge=0, description="Total number of classified service integration findings"
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


class GDPRServiceIntegrationFindingOutput(BaseSchemaOutput):
    """Complete output structure for gdpr_service_integration schema.

    This model represents the full wire format for GDPR service integration
    classification results, including findings enriched with GDPR-specific
    information, summary statistics, and analysis metadata.
    """

    __schema_version__: ClassVar[str] = "1.0.0"

    findings: list[GDPRServiceIntegrationFindingModel] = Field(
        description="List of service integration findings with GDPR classification"
    )
    summary: GDPRServiceIntegrationSummary = Field(
        description="Summary statistics of the GDPR classification analysis"
    )
    analysis_metadata: BaseAnalysisOutputMetadata = Field(
        description="Metadata about the classification process"
    )


__all__ = [
    "BaseFindingEvidence",
    "GDPRServiceIntegrationFindingMetadata",
    "GDPRServiceIntegrationFindingModel",
    "GDPRServiceIntegrationFindingOutput",
    "GDPRServiceIntegrationSummary",
]
