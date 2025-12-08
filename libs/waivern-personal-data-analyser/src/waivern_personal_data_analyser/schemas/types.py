"""Schema data models for personal data findings."""

from typing import ClassVar

from pydantic import BaseModel, Field
from waivern_core.schemas import (
    BaseAnalysisOutputMetadata,
    BaseFindingMetadata,
    BaseFindingModel,
    BaseSchemaOutput,
)


class PersonalDataFindingMetadata(BaseFindingMetadata):
    """Metadata for personal data findings.

    Extends BaseFindingMetadata which provides:
    - source: str - Source file or location where the data was found
    - context: dict[str, object] - Extensible context for pipeline metadata
    """

    pass


class PersonalDataFindingModel(BaseFindingModel):
    """Personal data finding structure."""

    type: str = Field(
        description="Type of personal data found (e.g., 'email', 'phone_number')"
    )
    data_type: str = Field(
        description="Categorical data type identifier from GDPR classification (e.g., 'basic_profile', 'health_data')"
    )
    special_category: bool = Field(
        default=False,
        description="Whether this is GDPR Article 9 special category data",
    )
    metadata: PersonalDataFindingMetadata | None = Field(
        default=None, description="Additional metadata from the original data source"
    )


class PersonalDataSummary(BaseModel):
    """Summary statistics for personal data findings."""

    total_findings: int = Field(
        ge=0, description="Total number of personal data findings"
    )
    high_risk_count: int = Field(
        ge=0, description="Number of high-risk personal data findings"
    )
    special_category_count: int = Field(
        ge=0, description="Number of special category personal data findings under GDPR"
    )


class PersonalDataValidationSummary(BaseModel):
    """LLM validation summary for personal data findings."""

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
    validation_mode: str = Field(description="LLM validation mode used")


class PersonalDataFindingOutput(BaseSchemaOutput):
    """Complete output structure for personal_data_finding schema.

    This model represents the full wire format for personal data analysis results,
    including findings, summary statistics, and analysis metadata.
    """

    __schema_version__: ClassVar[str] = "1.0.0"

    findings: list[PersonalDataFindingModel] = Field(
        description="List of personal data findings from GDPR compliance analysis"
    )
    summary: PersonalDataSummary = Field(
        description="Summary statistics of the personal data analysis"
    )
    analysis_metadata: BaseAnalysisOutputMetadata = Field(
        description="Metadata about the analysis process"
    )
    validation_summary: PersonalDataValidationSummary | None = Field(
        default=None, description="LLM validation summary (if validation was applied)"
    )
