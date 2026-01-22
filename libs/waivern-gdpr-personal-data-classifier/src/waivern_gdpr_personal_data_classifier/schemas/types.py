"""Schema data models for GDPR personal data classification findings."""

from typing import ClassVar, Literal, override

from pydantic import BaseModel, Field
from waivern_core.schemas import (
    BaseAnalysisOutputMetadata,
    BaseFindingEvidence,
    BaseFindingMetadata,
    BaseFindingModel,
    BaseSchemaOutput,
)


class GDPRPersonalDataFindingMetadata(BaseFindingMetadata):
    """Metadata for GDPR personal data classification findings.

    Extends BaseFindingMetadata which provides:
    - source: str - Source file or location where the data was found
    - context: dict[str, object] - Extensible context for pipeline metadata
    """

    pass


class GDPRPersonalDataFindingModel(BaseFindingModel[GDPRPersonalDataFindingMetadata]):
    """GDPR personal data classification finding structure.

    Represents a personal data indicator that has been enriched with
    GDPR-specific classification information. Risk is indicated by
    special_category - Article 9 special category data requires
    additional protections under GDPR.

    Note: privacy_category values are NOT GDPR-defined terms - they're from
    legal team for reporting/governance purposes. GDPR only mandates the
    distinction between personal data (Article 4) and special category (Article 9).

    Inherits from BaseFindingModel[GDPRPersonalDataFindingMetadata] which provides:
    - id: str - Unique identifier (auto-generated UUID)
    - evidence: list[BaseFindingEvidence] - Evidence items with content
    - matched_patterns: list[PatternMatchDetail] - Patterns that matched
    - metadata: GDPRPersonalDataFindingMetadata - Required metadata with source
    """

    # Original indicator information
    indicator_type: str = Field(
        description="Original personal data indicator category (e.g., 'email', 'health')"
    )

    # GDPR classification fields
    privacy_category: str = Field(
        description="Privacy category for reporting (e.g., 'identification_data', 'health_data')"
    )
    special_category: bool = Field(
        default=False,
        description="Whether this is GDPR Article 9 special category data (high risk)",
    )
    article_references: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Relevant GDPR article references (e.g., 'Article 9(1)', 'Article 4(1)')",
    )
    lawful_bases: tuple[
        Literal[
            "consent",
            "contract",
            "legal_obligation",
            "vital_interests",
            "public_task",
            "legitimate_interests",
        ],
        ...,
    ] = Field(
        default_factory=tuple,
        description="Applicable GDPR Article 6 lawful bases for processing",
    )

    @override
    def __str__(self) -> str:
        """Human-readable representation for logging and debugging."""
        return f"{self.indicator_type} ({self.privacy_category}) - {', '.join(p.pattern for p in self.matched_patterns)}"


class GDPRPersonalDataSummary(BaseModel):
    """Summary statistics for GDPR personal data classification findings."""

    total_findings: int = Field(
        ge=0, description="Total number of classified personal data findings"
    )
    special_category_count: int = Field(
        ge=0,
        description="Number of GDPR Article 9 special category data (high risk under GDPR)",
    )


class GDPRPersonalDataFindingOutput(BaseSchemaOutput):
    """Complete output structure for gdpr_personal_data schema.

    This model represents the full wire format for GDPR personal data
    classification results, including findings enriched with GDPR-specific
    information, summary statistics, and analysis metadata.
    """

    __schema_version__: ClassVar[str] = "1.0.0"

    findings: list[GDPRPersonalDataFindingModel] = Field(
        description="List of personal data findings with GDPR classification"
    )
    summary: GDPRPersonalDataSummary = Field(
        description="Summary statistics of the GDPR classification analysis"
    )
    analysis_metadata: BaseAnalysisOutputMetadata = Field(
        description="Metadata about the classification process"
    )


__all__ = [
    "BaseFindingEvidence",
    "GDPRPersonalDataFindingMetadata",
    "GDPRPersonalDataFindingModel",
    "GDPRPersonalDataFindingOutput",
    "GDPRPersonalDataSummary",
]
