"""Schema data models for processing purpose findings."""

from pydantic import BaseModel, ConfigDict, Field
from waivern_core.schemas import BaseFindingModel


class ProcessingPurposeFindingMetadata(BaseModel):
    """Metadata for processing purpose findings."""

    source: str = Field(description="Source file or location where the data was found")

    model_config = ConfigDict(extra="forbid")


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
