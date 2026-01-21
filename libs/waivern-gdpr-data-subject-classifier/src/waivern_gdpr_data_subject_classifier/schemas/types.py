"""Schema data models for GDPR data subject classification findings."""

from typing import ClassVar, override

from pydantic import BaseModel, Field
from waivern_core.schemas import (
    BaseAnalysisOutputMetadata,
    BaseFindingEvidence,
    BaseFindingMetadata,
    BaseFindingModel,
    BaseSchemaOutput,
)


class GDPRDataSubjectFindingMetadata(BaseFindingMetadata):
    """Metadata for GDPR data subject classification findings.

    Extends BaseFindingMetadata which provides:
    - source: str - Source file or location where the data was found
    - context: dict[str, object] - Extensible context for pipeline metadata
    """

    pass


class GDPRDataSubjectFindingModel(BaseFindingModel):
    """GDPR data subject classification finding structure.

    Represents a data subject indicator that has been enriched with
    GDPR-specific classification information. Risk is indicated by
    risk_modifiers - e.g., minors (Article 8) or vulnerable individuals
    (Recital 75) require additional protections under GDPR.
    """

    # GDPR classification (from ruleset mapping)
    data_subject_category: str = Field(
        description="Normalised GDPR data subject category (e.g., 'employee', 'customer')"
    )
    article_references: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Relevant GDPR article references (e.g., 'Article 4(1)', 'Article 30(1)(c)')",
    )
    typical_lawful_bases: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Typical GDPR Article 6 lawful bases for processing this data subject type",
    )

    # Risk assessment (pattern-based detection from evidence)
    risk_modifiers: list[str] = Field(
        default_factory=list,
        description="Risk modifiers detected from context (e.g., 'minor', 'vulnerable_individual')",
    )

    # Propagated from indicator
    confidence_score: int = Field(
        ge=0, le=100, description="Confidence score from indicator detection (0-100)"
    )
    metadata: GDPRDataSubjectFindingMetadata | None = Field(
        default=None, description="Additional metadata from the original data source"
    )

    @override
    def __str__(self) -> str:
        """Human-readable representation for logging and debugging."""
        modifiers = (
            f" [{', '.join(self.risk_modifiers)}]" if self.risk_modifiers else ""
        )
        return f"{self.data_subject_category}{modifiers} - {', '.join(p.pattern for p in self.matched_patterns)}"


class GDPRDataSubjectSummary(BaseModel):
    """Summary statistics for GDPR data subject classification findings."""

    total_findings: int = Field(
        ge=0, description="Total number of classified data subject findings"
    )
    categories_identified: list[str] = Field(
        default_factory=list,
        description="Unique data subject categories identified",
    )
    high_risk_count: int = Field(
        ge=0,
        description="Number of findings with risk modifiers (e.g., minors, vulnerable individuals)",
    )


class GDPRDataSubjectFindingOutput(BaseSchemaOutput):
    """Complete output structure for gdpr_data_subject schema.

    This model represents the full wire format for GDPR data subject
    classification results, including findings enriched with GDPR-specific
    information, summary statistics, and analysis metadata.
    """

    __schema_version__: ClassVar[str] = "1.0.0"

    findings: list[GDPRDataSubjectFindingModel] = Field(
        description="List of data subject findings with GDPR classification"
    )
    summary: GDPRDataSubjectSummary = Field(
        description="Summary statistics of the GDPR classification analysis"
    )
    analysis_metadata: BaseAnalysisOutputMetadata = Field(
        description="Metadata about the classification process"
    )


__all__ = [
    "BaseFindingEvidence",
    "GDPRDataSubjectFindingMetadata",
    "GDPRDataSubjectFindingModel",
    "GDPRDataSubjectFindingOutput",
    "GDPRDataSubjectSummary",
]
