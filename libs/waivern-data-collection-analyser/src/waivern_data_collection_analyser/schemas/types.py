"""Schema data models for data collection indicators."""

from typing import ClassVar, override

from pydantic import BaseModel, Field
from waivern_core.schemas import (
    BaseAnalysisOutputMetadata,
    BaseFindingMetadata,
    BaseFindingModel,
    BaseSchemaOutput,
)


class DataCollectionIndicatorMetadata(BaseFindingMetadata):
    """Metadata for data collection indicators.

    Extends BaseFindingMetadata which provides:
    - source: str - Source file or location where the data was found
    - context: dict[str, object] - Extensible context for pipeline metadata
    """

    line_number: int | None = Field(
        default=None,
        description="Line number where the indicator was detected (for source code)",
    )


class DataCollectionIndicatorModel(BaseFindingModel[DataCollectionIndicatorMetadata]):
    """Data collection indicator structure.

    A framework-agnostic indicator of a detected data collection mechanism.
    Regulatory classification (e.g., GDPR category) is performed by
    downstream classifiers.

    Inherits from BaseFindingModel[DataCollectionIndicatorMetadata] which provides:
    - id: str - Unique identifier (auto-generated UUID)
    - evidence: list[BaseFindingEvidence] - Evidence items with content
    - matched_patterns: list[PatternMatchDetail] - Patterns that matched
    - metadata: DataCollectionIndicatorMetadata - Required metadata with source
    - require_review: bool | None - Whether this finding requires human review
    """

    collection_type: str = Field(
        description="Type of data collection (e.g. 'form_data', 'cookies')",
    )
    data_source: str = Field(
        description="Source of the data (e.g. 'http_post', 'browser_cookies')",
    )

    @override
    def __str__(self) -> str:
        """Human-readable representation for logging and debugging."""
        return f"{self.collection_type}/{self.data_source} - {', '.join(p.pattern for p in self.matched_patterns)}"


class CollectionTypeBreakdown(BaseModel):
    """Per-collection-type breakdown of indicators."""

    collection_type: str = Field(description="Collection type slug")
    findings_count: int = Field(
        ge=0, description="Number of indicators for this collection type"
    )


class DataCollectionIndicatorSummary(BaseModel):
    """Summary statistics for data collection indicators."""

    total_findings: int = Field(
        ge=0, description="Total number of data collection indicators"
    )
    categories_identified: int = Field(
        ge=0, description="Number of unique collection types identified"
    )
    categories: list[CollectionTypeBreakdown] = Field(
        default_factory=list,
        description="Per-collection-type breakdown of indicators",
    )


class DataCollectionIndicatorOutput(BaseSchemaOutput):
    """Complete output structure for data_collection_indicator schema.

    This model represents the full wire format for data collection analysis
    results, including indicators, summary statistics, and analysis metadata.
    """

    __schema_version__: ClassVar[str] = "1.0.0"

    findings: list[DataCollectionIndicatorModel] = Field(
        description="List of data collection indicators from analysis"
    )
    summary: DataCollectionIndicatorSummary = Field(
        description="Summary statistics of the data collection analysis"
    )
    analysis_metadata: BaseAnalysisOutputMetadata = Field(
        description="Metadata about the analysis process"
    )
