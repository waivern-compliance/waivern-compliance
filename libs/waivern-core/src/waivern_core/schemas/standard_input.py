"""Standard input schema for WCT.

This module defines Pydantic models for the standard_input schema,
which represents the common input format used by most WCT connectors.

To use the schema, instantiate it with:
    schema = Schema("standard_input", "1.0.0")
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from waivern_core.schemas.connector_types import BaseMetadata


class StandardInputDataItemModel[MetadataT: BaseMetadata](BaseModel):
    """Individual data item in standard_input schema."""

    content: str = Field(description="The actual content/data")
    metadata: MetadataT = Field(description="Metadata about the data item")


class StandardInputDataModel[MetadataT: BaseMetadata](BaseModel):
    """Complete structure of standard_input schema data."""

    schemaVersion: str = Field(description="Schema version identifier")
    name: str = Field(description="Name/identifier for this data set")
    data: list[StandardInputDataItemModel[MetadataT]] = Field(
        description="List of data items"
    )
    description: str | None = Field(default=None, description="Optional description")
    contentEncoding: str | None = Field(
        default=None, description="Content encoding if applicable"
    )
    source: str | None = Field(default=None, description="Source of the data")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
