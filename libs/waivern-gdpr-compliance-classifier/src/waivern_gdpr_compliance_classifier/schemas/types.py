"""Schema data models for GDPR compliance classification findings."""

from typing import ClassVar, Literal, override

from pydantic import BaseModel, Field
from waivern_core.schemas import (
    BaseAnalysisOutputMetadata,
    BaseFindingEvidence,
    BaseFindingMetadata,
    BaseFindingModel,
    BaseSchemaOutput,
)


class GDPRComplianceClassificationFindingMetadata(BaseFindingMetadata):
    """Metadata for GDPR compliance classification findings.

    Extends BaseFindingMetadata which provides:
    - source: str - Source file or location where the data was found
    - context: dict[str, object] - Extensible context for pipeline metadata
    """

    pass


class GDPRComplianceClassificationFindingModel(
    BaseFindingModel[GDPRComplianceClassificationFindingMetadata]
):
    """GDPR compliance classification finding structure.

    Represents an indicator finding that has been enriched with
    GDPR-specific classification information. Sensitive purposes (e.g., AI/ML,
    analytics, marketing) may require additional considerations such as
    explicit consent or DPIA under GDPR.

    Inherits from BaseFindingModel[GDPRComplianceClassificationFindingMetadata] which provides:
    - id: str - Unique identifier (auto-generated UUID)
    - evidence: list[BaseFindingEvidence] - Evidence items with content
    - matched_patterns: list[PatternMatchDetail] - Patterns that matched
    - metadata: GDPRComplianceClassificationFindingMetadata - Required metadata with source
    - require_review: bool | None - Whether this finding requires human review
    """

    # Original indicator data (propagated)
    indicator_value: str = Field(
        description="Indicator value from upstream analyser (e.g., processing purpose name, service category)"
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
        return f"{self.indicator_value} → {self.purpose_category}{sensitive}"


class GDPRComplianceClassificationSummary(BaseModel):
    """Summary statistics for GDPR compliance classification findings."""

    total_findings: int = Field(ge=0, description="Total number of classified findings")
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
    requires_review_count: int = Field(
        ge=0,
        description="Number of findings that require human review to determine actual processing purpose",
    )


class GDPRComplianceClassificationOutput(BaseSchemaOutput):
    """Complete output structure for gdpr_compliance_classification schema.

    This model represents the full wire format for GDPR compliance
    classification results, including findings enriched with GDPR-specific
    information, summary statistics, and analysis metadata.
    """

    __schema_version__: ClassVar[str] = "1.0.0"

    findings: list[GDPRComplianceClassificationFindingModel] = Field(
        description="List of findings with GDPR classification"
    )
    summary: GDPRComplianceClassificationSummary = Field(
        description="Summary statistics of the GDPR classification analysis"
    )
    analysis_metadata: BaseAnalysisOutputMetadata = Field(
        description="Metadata about the classification process"
    )


__all__ = [
    "BaseFindingEvidence",
    "GDPRComplianceClassificationFindingMetadata",
    "GDPRComplianceClassificationFindingModel",
    "GDPRComplianceClassificationOutput",
    "GDPRComplianceClassificationSummary",
]
