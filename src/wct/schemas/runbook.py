"""Runbook schema for WCT.

This module defines the RunbookSchema class that represents
the runbook configuration format used by WCT.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .base import JsonSchemaLoader, Schema, SchemaLoader


@dataclass(frozen=True, slots=True)
class RunbookSchema(Schema):
    """Schema for WCT runbook configuration files.

    This schema defines the structure and validation rules for YAML-based
    runbook files that specify WCT analysis pipelines.
    """

    _VERSION = "1.0.0"

    _loader: SchemaLoader = field(default_factory=JsonSchemaLoader, init=False)

    @property
    def name(self) -> str:
        """Return the schema name."""
        return "runbook"

    @property
    def version(self) -> str:
        """Return the schema version."""
        return self._VERSION

    @property
    def schema(self) -> dict[str, Any]:
        """Return the JSON schema definition for validation."""
        return self._loader.load(self.name, self.version)
