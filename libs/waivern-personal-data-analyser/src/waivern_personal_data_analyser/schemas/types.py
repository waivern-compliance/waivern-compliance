"""Schema data models for personal data findings."""

from pydantic import BaseModel, ConfigDict, Field
from waivern_core.schemas import BaseFindingModel


class PersonalDataFindingMetadata(BaseModel):
    """Metadata for personal data findings that matches the JSON schema."""

    source: str = Field(description="Source file or location where the data was found")

    model_config = ConfigDict(extra="forbid")


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
