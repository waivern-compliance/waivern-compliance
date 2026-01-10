"""Schema data models for data subject findings."""

from typing import ClassVar, override

from pydantic import BaseModel, Field
from waivern_core.schemas import (
    BaseAnalysisOutputMetadata,
    BaseFindingMetadata,
    BaseFindingModel,
    BaseSchemaOutput,
)


class DataSubjectFindingMetadata(BaseFindingMetadata):
    """Metadata for data subject findings.

    Extends BaseFindingMetadata which provides:
    - source: str - Source file or location where the data was found
    - context: dict[str, object] - Extensible context for pipeline metadata
    """

    pass


class DataSubjectFindingModel(BaseFindingModel):
    """Data subject finding structure."""

    primary_category: str = Field(description="Primary data subject category")
    confidence_score: int = Field(
        ge=0, le=100, description="Confidence score for the classification (0-100)"
    )
    modifiers: list[str] = Field(
        default_factory=list,
        description="Cross-category regulatory modifiers from ruleset",
    )
    metadata: DataSubjectFindingMetadata | None = Field(
        default=None, description="Additional metadata about the finding"
    )

    @override
    def __str__(self) -> str:
        """Human-readable representation for logging and debugging."""
        return f"{self.primary_category} - {', '.join(self.matched_patterns)}"


class DataSubjectSummary(BaseModel):
    """Summary statistics for data subject findings."""

    total_classifications: int = Field(
        ge=0, description="Total number of data subject classifications"
    )
    categories_identified: list[str] = Field(
        description="List of unique categories identified"
    )


class DataSubjectFindingOutput(BaseSchemaOutput):
    """Complete output structure for data_subject_finding schema.

    This model represents the full wire format for data subject analysis results,
    including findings, summary statistics, and analysis metadata.
    """

    __schema_version__: ClassVar[str] = "1.0.0"

    findings: list[DataSubjectFindingModel] = Field(
        description="List of data subject findings from GDPR compliance analysis"
    )
    summary: DataSubjectSummary = Field(
        description="Summary statistics of the data subject analysis"
    )
    analysis_metadata: BaseAnalysisOutputMetadata = Field(
        description="Metadata about the analysis process"
    )
