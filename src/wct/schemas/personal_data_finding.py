"""Personal data finding schema for WCT.

This module defines the PersonalDataFindingSchema class that represents
the output format for personal data analysis results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, override

from .base import JsonSchemaLoader, Schema, SchemaLoader


@dataclass(frozen=True, slots=True)
class PersonalDataFindingSchema(Schema):
    """Schema for personal data finding results.

    This schema represents the structured format used by personal data
    analysers to report findings about personal data discovered in
    various data sources.
    """

    _VERSION = "1.0.0"

    _loader: SchemaLoader = field(default_factory=JsonSchemaLoader, init=False)

    @property
    @override
    def name(self) -> str:
        """Return the schema name."""
        return "personal_data_finding"

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
