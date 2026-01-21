"""Schema data models for data subject indicators."""

from typing import ClassVar, override

from pydantic import BaseModel, Field
from waivern_core.schemas import (
    BaseAnalysisOutputMetadata,
    BaseFindingMetadata,
    BaseFindingModel,
    BaseSchemaOutput,
)


class DataSubjectIndicatorMetadata(BaseFindingMetadata):
    """Metadata for data subject indicators.

    Extends BaseFindingMetadata which provides:
    - source: str - Source file or location where the data was found
    - context: dict[str, object] - Extensible context for pipeline metadata
    """

    line_number: int | None = Field(
        default=None,
        description="Line number where the indicator was detected (for source code findings)",
    )


class DataSubjectIndicatorModel(BaseFindingModel):
    """Data subject indicator from pattern-based detection."""

    subject_category: str = Field(description="Data subject category detected")
    confidence_score: int = Field(
        ge=0, le=100, description="Confidence score for the detection (0-100)"
    )
    metadata: DataSubjectIndicatorMetadata | None = Field(
        default=None, description="Additional metadata about the indicator"
    )

    @override
    def __str__(self) -> str:
        """Human-readable representation for logging and debugging."""
        return f"{self.subject_category} - {', '.join(p.pattern for p in self.matched_patterns)}"


class DataSubjectIndicatorSummary(BaseModel):
    """Summary statistics for data subject indicators."""

    total_indicators: int = Field(
        ge=0, description="Total number of data subject indicators detected"
    )
    categories_identified: list[str] = Field(
        description="List of unique categories identified"
    )


class DataSubjectIndicatorOutput(BaseSchemaOutput):
    """Complete output structure for data_subject_indicator schema.

    This model represents the full wire format for data subject detection results,
    including indicators, summary statistics, and analysis metadata.
    """

    __schema_version__: ClassVar[str] = "1.0.0"

    findings: list[DataSubjectIndicatorModel] = Field(
        description="List of data subject indicators from pattern-based detection"
    )
    summary: DataSubjectIndicatorSummary = Field(
        description="Summary statistics of the data subject detection"
    )
    analysis_metadata: BaseAnalysisOutputMetadata = Field(
        description="Metadata about the analysis process"
    )
