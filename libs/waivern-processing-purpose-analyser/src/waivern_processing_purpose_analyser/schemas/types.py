"""Schema data models for processing purpose findings."""

from typing import ClassVar

from pydantic import BaseModel, Field
from waivern_core.schemas import (
    BaseAnalysisOutputMetadata,
    BaseFindingMetadata,
    BaseFindingModel,
    BaseSchemaOutput,
)


class ProcessingPurposeFindingMetadata(BaseFindingMetadata):
    """Metadata for processing purpose findings.

    Extends BaseFindingMetadata which provides:
    - source: str - Source file or location where the data was found
    - context: dict[str, object] - Extensible context for pipeline metadata
    """

    pass


class ProcessingPurposeFindingModel(BaseFindingModel):
    """Processing purpose finding structure."""

    purpose: str = Field(description="Processing purpose name")
    purpose_category: str = Field(
        default="", description="Category of the processing purpose"
    )
    metadata: ProcessingPurposeFindingMetadata | None = Field(
        default=None, description="Additional metadata about the finding"
    )
    service_category: str | None = Field(
        default=None,
        description="Service category from ServiceIntegrationRule (when applicable)",
    )
    collection_type: str | None = Field(
        default=None,
        description="Collection type from DataCollectionRule (when applicable)",
    )
    data_source: str | None = Field(
        default=None,
        description="Data source from DataCollectionRule (when applicable)",
    )


class ProcessingPurposeSummary(BaseModel):
    """Summary statistics for processing purpose findings."""

    total_findings: int = Field(
        ge=0, description="Total number of processing purpose findings"
    )
    purposes_identified: int = Field(
        ge=0, description="Number of unique processing purposes identified"
    )
    high_risk_count: int = Field(
        ge=0, description="Number of high risk processing purpose findings"
    )
    purpose_categories: dict[str, int] = Field(
        description="Count of findings by purpose category"
    )
    risk_level_distribution: dict[str, int] = Field(
        description="Distribution of findings by risk level"
    )


class ProcessingPurposeValidationSummary(BaseModel):
    """LLM validation summary for processing purpose findings."""

    llm_validation_enabled: bool = Field(
        default=True, description="Whether LLM validation was enabled"
    )
    original_findings_count: int = Field(
        ge=0, description="Number of findings before validation"
    )
    validated_findings_count: int = Field(
        ge=0, description="Number of findings after validation"
    )
    false_positives_removed: int = Field(
        ge=0, description="Number of false positives removed by validation"
    )
    validation_effectiveness_percentage: float = Field(
        ge=0.0,
        le=100.0,
        description="Percentage of findings identified as false positives",
    )
    validation_mode: str = Field(description="LLM validation mode used")
    removed_purposes: list[str] = Field(
        default_factory=list, description="List of purposes that were removed"
    )


class ProcessingPurposeFindingOutput(BaseSchemaOutput):
    """Complete output structure for processing_purpose_finding schema.

    This model represents the full wire format for processing purpose analysis results,
    including findings, summary statistics, and analysis metadata.
    """

    __schema_version__: ClassVar[str] = "1.0.0"

    findings: list[ProcessingPurposeFindingModel] = Field(
        description="List of processing purpose findings from GDPR compliance analysis"
    )
    summary: ProcessingPurposeSummary = Field(
        description="Summary statistics of the processing purpose analysis"
    )
    analysis_metadata: BaseAnalysisOutputMetadata = Field(
        description="Metadata about the analysis process"
    )
    validation_summary: ProcessingPurposeValidationSummary | None = Field(
        default=None,
        description="LLM validation summary (if validation was applied)",
    )
