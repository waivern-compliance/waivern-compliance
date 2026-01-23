"""Schema data models for processing purpose indicators."""

from typing import ClassVar, Literal, override

SourceCodeContextWindow = Literal["small", "medium", "large", "full"]

from pydantic import BaseModel, Field
from waivern_core.schemas import (
    BaseAnalysisOutputMetadata,
    BaseFindingMetadata,
    BaseFindingModel,
    BaseSchemaOutput,
)


class ProcessingPurposeIndicatorMetadata(BaseFindingMetadata):
    """Metadata for processing purpose indicators.

    Extends BaseFindingMetadata which provides:
    - source: str - Source file or location where the data was found
    - context: dict[str, object] - Extensible context for pipeline metadata
    """

    line_number: int | None = Field(
        default=None,
        description="Line number where the indicator was detected (for source code)",
    )


class ProcessingPurposeIndicatorModel(
    BaseFindingModel[ProcessingPurposeIndicatorMetadata]
):
    """Processing purpose indicator structure.

    A framework-agnostic indicator of a detected processing purpose.
    Regulatory classification (e.g., GDPR category) is performed by
    downstream classifiers.

    Inherits from BaseFindingModel[ProcessingPurposeIndicatorMetadata] which provides:
    - id: str - Unique identifier (auto-generated UUID)
    - evidence: list[BaseFindingEvidence] - Evidence items with content
    - matched_patterns: list[PatternMatchDetail] - Patterns that matched
    - metadata: ProcessingPurposeIndicatorMetadata - Required metadata with source
    """

    purpose: str = Field(description="Processing purpose name (from ruleset)")

    # Technical metadata about data collection mechanism (optional, from DataCollectionRule)
    # These are framework-agnostic and useful for auditing across compliance frameworks
    collection_type: str | None = Field(
        default=None,
        description="Technical mechanism of data collection (e.g., form_data, cookies, api_endpoint)",
    )
    data_source: str | None = Field(
        default=None,
        description="Origin of collected data (e.g., http_request, browser_storage)",
    )

    @override
    def __str__(self) -> str:
        """Human-readable representation for logging and debugging."""
        return f"{self.purpose} - {', '.join(p.pattern for p in self.matched_patterns)}"


class PurposeBreakdown(BaseModel):
    """Per-purpose breakdown of indicators."""

    purpose: str = Field(description="Purpose name")
    findings_count: int = Field(
        ge=0, description="Number of indicators for this purpose"
    )


class ProcessingPurposeIndicatorSummary(BaseModel):
    """Summary statistics for processing purpose indicators."""

    total_findings: int = Field(
        ge=0, description="Total number of processing purpose indicators"
    )
    purposes_identified: int = Field(
        ge=0, description="Number of unique processing purposes identified"
    )
    purposes: list[PurposeBreakdown] = Field(
        default_factory=list,
        description="Per-purpose breakdown of indicators",
    )


class ProcessingPurposeIndicatorOutput(BaseSchemaOutput):
    """Complete output structure for processing_purpose_indicator schema.

    This model represents the full wire format for processing purpose analysis results,
    including indicators, summary statistics, and analysis metadata.
    """

    __schema_version__: ClassVar[str] = "1.0.0"

    findings: list[ProcessingPurposeIndicatorModel] = Field(
        description="List of processing purpose indicators from analysis"
    )
    summary: ProcessingPurposeIndicatorSummary = Field(
        description="Summary statistics of the processing purpose analysis"
    )
    analysis_metadata: BaseAnalysisOutputMetadata = Field(
        description="Metadata about the analysis process"
    )
