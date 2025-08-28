"""Processing purpose finding schema for WCT.

This module defines the ProcessingPurposeFindingSchema class that represents
the output format for processing purpose analysis results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from typing_extensions import override

from .base import JsonSchemaLoader, Schema, SchemaLoader


@dataclass(frozen=True, slots=True)
class ProcessingPurposeFindingSchema(Schema):
    """Schema for processing purpose finding results.

    This schema represents the structured format used by processing purpose
    analysers to report findings about GDPR processing purposes discovered
    in various data sources and code analysis.
    """

    _VERSION = "1.0.0"

    _loader: SchemaLoader = field(default_factory=JsonSchemaLoader, init=False)

    @property
    @override
    def name(self) -> str:
        """Return the schema name."""
        return "processing_purpose_finding"

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
