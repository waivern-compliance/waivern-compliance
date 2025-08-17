"""Data models for personal data analysis analyser."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PersonalDataFindingMetadata(BaseModel):
    """Metadata for personal data findings that matches the JSON schema."""

    source: str = Field(description="Source file or location where the data was found")

    model_config = ConfigDict(extra="allow")


class PersonalDataFindingModel(BaseModel):
    """Personal data finding structure."""

    type: str = Field(
        description="Type of personal data found (e.g., 'email', 'phone_number')"
    )
    risk_level: str = Field(description="Risk assessment level (low, medium, high)")
    special_category: str | None = Field(
        default=None, description="GDPR special category indicator (Y/N)"
    )
    matched_pattern: str = Field(
        description="Specific pattern that matched in the content"
    )
    evidence: list[str] | None = Field(
        default=None,
        description="Evidence snippets from content that matches this finding",
    )
    metadata: PersonalDataFindingMetadata | None = Field(
        default=None, description="Additional metadata from the original data source"
    )

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, v: str) -> str:
        """Validate risk level values."""
        allowed = ["low", "medium", "high"]
        if v not in allowed:
            raise ValueError(f"risk_level must be one of {allowed}, got: {v}")
        return v
