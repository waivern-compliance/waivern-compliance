"""Data subject finding schema for WCT.

This module defines the DataSubjectFindingSchema class that represents
the output format for data subject analysis results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, override

from .base import JsonSchemaLoader, Schema, SchemaLoader


@dataclass(frozen=True, slots=True)
class DataSubjectFindingSchema(Schema):
    """Schema for data subject finding results.

    This schema represents the structured format used by data subject
    analysers to report findings about data subject categories discovered
    in various data sources for GDPR Article 30(1)(c) compliance.
    """

    _VERSION = "1.0.0"

    _loader: SchemaLoader = field(default_factory=JsonSchemaLoader, init=False)

    @property
    @override
    def name(self) -> str:
        """Return the schema name."""
        return "data_subject_finding"

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
