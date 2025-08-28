"""Standard input schema for WCT.

This module defines the StandardInputSchema class that represents
the standard input format used by most WCT connectors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import override

from .base import JsonSchemaLoader, Schema, SchemaLoader


class StandardInputDataItemMetadataModel(BaseModel):
    """Metadata for a data item in standard_input schema."""

    source: str = Field(description="Source identifier for the data item")

    model_config = ConfigDict(
        extra="allow"
    )  # Allow additional properties not explicitly defined


class StandardInputDataItemModel(BaseModel):
    """Individual data item in standard_input schema."""

    content: str = Field(description="The actual content/data")
    metadata: StandardInputDataItemMetadataModel = Field(
        description="Metadata about the data item"
    )


class StandardInputDataModel(BaseModel):
    """Complete structure of standard_input schema data."""

    schemaVersion: str = Field(description="Schema version identifier")
    name: str = Field(description="Name/identifier for this data set")
    data: list[StandardInputDataItemModel] = Field(description="List of data items")
    description: str | None = Field(default=None, description="Optional description")
    contentEncoding: str | None = Field(
        default=None, description="Content encoding if applicable"
    )
    source: str | None = Field(default=None, description="Source of the data")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


@dataclass(frozen=True, slots=True)
class StandardInputSchema(Schema):
    """Schema for standard input data format.

    This schema represents the common input format used by filesystem
    connectors and other basic data sources.
    """

    _VERSION = "1.0.0"

    _loader: SchemaLoader = field(default_factory=JsonSchemaLoader, init=False)

    @property
    @override
    def name(self) -> str:
        """Return the schema name."""
        return "standard_input"

    @property
    @override
    def version(self) -> str:
        """Return the schema version."""
        return self._VERSION

    @property
    @override
    def schema(self) -> dict[str, Any]:
        """Return the JSON schema definition for validation."""
        return self._loader.load(self.name, self.version)
