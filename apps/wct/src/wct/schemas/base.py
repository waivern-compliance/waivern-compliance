"""WCT-specific schema base classes.

This module provides WCT-specific schema abstractions that extend the
framework-level schemas from waivern-core.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, override

from waivern_core.schemas.base import JsonSchemaLoader, Schema, SchemaLoader


@dataclass(frozen=True, slots=True, eq=False)
class BaseFindingSchema(Schema, ABC):
    """Base schema for all WCT finding result types.

    This abstract schema provides the common structure that all WCT analyser
    finding outputs share: findings array, summary object, and analysis metadata.

    This is a WCT-specific concept - "finding" represents discovered compliance
    issues or data items during analysis.
    """

    _loader: SchemaLoader = field(default_factory=JsonSchemaLoader, init=False)

    @property
    @abstractmethod
    @override
    def name(self) -> str:
        """Return the unique identifier for this schema."""

    @property
    @abstractmethod
    @override
    def version(self) -> str:
        """Return the version for this schema."""

    @property
    @override
    def schema(self) -> dict[str, Any]:
        """Return the JSON schema definition for validation."""
        return self._loader.load(self.name, self.version)
