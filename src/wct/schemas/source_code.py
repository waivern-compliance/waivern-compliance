"""Source code schema for WCT.

This module defines the SourceCodeSchema class that represents
the source code analysis format used by source code connectors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .base import JsonSchemaLoader, Schema, SchemaLoader


@dataclass(frozen=True, slots=True)
class SourceCodeSchema(Schema):
    """Schema for source code analysis data format.

    This schema represents the structured format used by source code
    connectors for analysing programming languages and extracting
    relevant compliance information.
    """

    _VERSION = "1.0.0"

    _loader: SchemaLoader = field(default_factory=JsonSchemaLoader, init=False)

    @property
    def name(self) -> str:
        """Return the schema name."""
        return "source_code"

    @property
    def version(self) -> str:
        """Return the schema version."""
        return self._VERSION

    @property
    def schema(self) -> dict[str, Any]:
        """Return the JSON schema definition for validation."""
        return self._loader.load(self.name, self.version)
