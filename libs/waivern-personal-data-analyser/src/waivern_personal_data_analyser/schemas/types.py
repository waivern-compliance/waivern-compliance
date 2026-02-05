"""Schema data models for personal data indicator findings."""

from typing import ClassVar, override

from pydantic import BaseModel, Field
from waivern_core.schemas import (
    BaseAnalysisOutputMetadata,
    BaseFindingMetadata,
    BaseFindingModel,
    BaseSchemaOutput,
)


class PersonalDataIndicatorMetadata(BaseFindingMetadata):
    """Metadata for personal data indicator findings.

    Extends BaseFindingMetadata which provides:
    - source: str - Source file or location where the data was found
    - context: dict[str, object] - Extensible context for pipeline metadata
    """

    pass


class PersonalDataIndicatorModel(BaseFindingModel[PersonalDataIndicatorMetadata]):
    """Personal data indicator finding structure.

    This is a framework-agnostic indicator that identifies personal data patterns.
    Regulatory classification (e.g., GDPR special categories) is performed by
    downstream classifiers.

    Inherits from BaseFindingModel[PersonalDataIndicatorMetadata] which provides:
    - id: str - Unique identifier (auto-generated UUID)
    - evidence: list[BaseFindingEvidence] - Evidence items with content
    - matched_patterns: list[PatternMatchDetail] - Patterns that matched
    - metadata: PersonalDataIndicatorMetadata - Required metadata with source
    - require_review: bool | None - Whether this finding requires human review
    """

    category: str = Field(
        description="Category of personal data (e.g., 'email', 'phone', 'health')"
    )

    @override
    def __str__(self) -> str:
        """Human-readable representation for logging and debugging."""
        return (
            f"{self.category} - {', '.join(p.pattern for p in self.matched_patterns)}"
        )


class PersonalDataIndicatorSummary(BaseModel):
    """Summary statistics for personal data indicator findings."""

    total_findings: int = Field(
        ge=0, description="Total number of personal data indicators found"
    )


class PersonalDataIndicatorOutput(BaseSchemaOutput):
    """Complete output structure for personal_data_indicator schema.

    This model represents the full wire format for personal data indicator results.
    These indicators are framework-agnostic and can be consumed by regulatory
    classifiers (e.g., GDPR, CCPA) for framework-specific enrichment.
    """

    __schema_version__: ClassVar[str] = "1.0.0"

    findings: list[PersonalDataIndicatorModel] = Field(
        description="List of personal data indicators found"
    )
    summary: PersonalDataIndicatorSummary = Field(
        description="Summary statistics of the personal data analysis"
    )
    analysis_metadata: BaseAnalysisOutputMetadata = Field(
        description="Metadata about the analysis process"
    )
