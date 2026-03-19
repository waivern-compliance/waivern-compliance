"""Schema data models for service integration indicators."""

from typing import ClassVar, override

from pydantic import BaseModel, Field
from waivern_core.schemas import (
    BaseAnalysisOutputMetadata,
    BaseFindingMetadata,
    BaseFindingModel,
    BaseSchemaOutput,
)


class ServiceIntegrationIndicatorMetadata(BaseFindingMetadata):
    """Metadata for service integration indicators.

    Extends BaseFindingMetadata which provides:
    - source: str - Source file or location where the data was found
    - context: dict[str, object] - Extensible context for pipeline metadata
    """

    line_number: int | None = Field(
        default=None,
        description="Line number where the indicator was detected (for source code)",
    )


class ServiceIntegrationIndicatorModel(
    BaseFindingModel[ServiceIntegrationIndicatorMetadata]
):
    """Service integration indicator structure.

    A framework-agnostic indicator of a detected third-party service integration.
    Regulatory classification (e.g., GDPR category) is performed by
    downstream classifiers.

    Inherits from BaseFindingModel[ServiceIntegrationIndicatorMetadata] which provides:
    - id: str - Unique identifier (auto-generated UUID)
    - evidence: list[BaseFindingEvidence] - Evidence items with content
    - matched_patterns: list[PatternMatchDetail] - Patterns that matched
    - metadata: ServiceIntegrationIndicatorMetadata - Required metadata with source
    - require_review: bool | None - Whether this finding requires human review
    """

    service_category: str = Field(
        description="Category of service integration (e.g. 'cloud_infrastructure', 'payment_processing')",
    )
    purpose_category: str = Field(
        description="Purpose category for compliance (e.g. 'operational', 'analytics')",
    )

    @override
    def __str__(self) -> str:
        """Human-readable representation for logging and debugging."""
        return f"{self.service_category}/{self.purpose_category} - {', '.join(p.pattern for p in self.matched_patterns)}"


class ServiceCategoryBreakdown(BaseModel):
    """Per-category breakdown of indicators."""

    service_category: str = Field(description="Service category slug")
    findings_count: int = Field(
        ge=0, description="Number of indicators for this category"
    )


class ServiceIntegrationIndicatorSummary(BaseModel):
    """Summary statistics for service integration indicators."""

    total_findings: int = Field(
        ge=0, description="Total number of service integration indicators"
    )
    categories_identified: int = Field(
        ge=0, description="Number of unique service categories identified"
    )
    categories: list[ServiceCategoryBreakdown] = Field(
        default_factory=list,
        description="Per-category breakdown of indicators",
    )


class ServiceIntegrationIndicatorOutput(BaseSchemaOutput):
    """Complete output structure for service_integration_indicator schema.

    This model represents the full wire format for service integration analysis
    results, including indicators, summary statistics, and analysis metadata.
    """

    __schema_version__: ClassVar[str] = "1.0.0"

    findings: list[ServiceIntegrationIndicatorModel] = Field(
        description="List of service integration indicators from analysis"
    )
    summary: ServiceIntegrationIndicatorSummary = Field(
        description="Summary statistics of the service integration analysis"
    )
    analysis_metadata: BaseAnalysisOutputMetadata = Field(
        description="Metadata about the analysis process"
    )
