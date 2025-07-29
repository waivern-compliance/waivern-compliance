"""Shared schema definitions for WCT connectors and plugins."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, TypeVar

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


def load_json_schema(schema_name: str) -> dict[str, Any]:
    """Load JSON schema from file.

    Args:
        schema_name: Name of the schema to load

    Returns:
        The JSON schema as a dictionary

    Raises:
        FileNotFoundError: If schema file doesn't exist
        SchemaLoadError: If schema file cannot be parsed
    """
    # Try multiple potential locations for schema files
    schema_paths = [
        Path("src/wct/schemas") / f"{schema_name}.json",
        Path("./src/wct/schemas") / f"{schema_name}.json",
        Path(__file__).parent / "schemas" / f"{schema_name}.json",
    ]

    for schema_path in schema_paths:
        if schema_path.exists():
            try:
                with open(schema_path) as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                raise SchemaLoadError(
                    f"Invalid JSON in schema file '{schema_path}': {e}"
                ) from e
            except OSError as e:
                raise SchemaLoadError(
                    f"Cannot read schema file '{schema_path}': {e}"
                ) from e

    raise FileNotFoundError(
        f"Schema file for '{schema_name}' not found in any of: {schema_paths}"
    )


class SchemaValidationError(Exception):
    """Base exception for schema validation errors."""

    pass


class SchemaLoadError(Exception):
    """Raised when schema files cannot be loaded or parsed."""

    pass
