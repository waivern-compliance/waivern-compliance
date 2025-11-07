"""Schema data models for data subject findings."""

from pydantic import BaseModel, ConfigDict, Field
from waivern_core.schemas import BaseFindingModel


class DataSubjectFindingMetadata(BaseModel):
    """Metadata for data subject findings."""

    source: str = Field(description="Source file or location where the data was found")

    model_config = ConfigDict(extra="forbid")


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
