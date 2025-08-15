"""Standard input schema for WCT.

This module defines the StandardInputSchema class that represents
the standard input format used by most WCT connectors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypedDict

from typing_extensions import NotRequired

from .base import JsonSchemaLoader, Schema, SchemaLoader


# Type definitions for standard_input schema data structures
class StandardInputDataItemMetadata(TypedDict):
    """Metadata for a data item in standard_input schema."""

    source: str  # Required by schema
    # Additional properties allowed but not typed


class StandardInputDataItem(TypedDict):
    """Individual data item in standard_input schema."""

    content: str
    metadata: StandardInputDataItemMetadata


class StandardInputData(TypedDict):
    """Complete structure of standard_input schema data."""

    schemaVersion: str
    name: str
    data: list[StandardInputDataItem]
    description: NotRequired[str]
    contentEncoding: NotRequired[str]
    source: NotRequired[str]
    metadata: NotRequired[dict[str, Any]]


@dataclass(frozen=True, slots=True)
class StandardInputSchema(Schema):
    """Schema for standard input data format.

    This schema represents the common input format used by filesystem
    connectors and other basic data sources.
    """

    _VERSION = "1.0.0"

    _loader: SchemaLoader = field(default_factory=JsonSchemaLoader, init=False)

    @property
    def name(self) -> str:
        """Return the schema name."""
        return "standard_input"

    @property
    def version(self) -> str:
        """Return the schema version."""
        return self._VERSION

    @property
    def schema(self) -> dict[str, Any]:
        """Return the JSON schema definition for validation."""
        return self._loader.load(self.name, self.version)
