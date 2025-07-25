"""Shared schema definitions for WCT connectors and plugins."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

_SchemaType = TypeVar("_SchemaType")


@dataclass(frozen=True, slots=True)
class WctSchema(Generic[_SchemaType]):
    """Information about a component's input or output schema.

    This class provides a consistent way to specify both the schema name
    (string identifier) and the expected data type for connectors and plugins.
    """

    name: str
    type: type[_SchemaType]
    schema_str: str | None = None
    """Schema definition (JSON Schema) as a string, if applicable."""


class SchemaValidationError(Exception):
    """Base exception for schema validation errors."""

    pass
