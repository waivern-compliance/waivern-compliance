"""Standard input schema for WCT.

This module defines the StandardInputSchema class that represents
the standard input format used by most WCT connectors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .base import JsonSchemaLoader, Schema, SchemaLoader


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
