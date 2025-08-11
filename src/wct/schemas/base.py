"""Base classes for WCT schemas.

This module provides the foundation for strongly typed schemas that replace
the generic WctSchema[T] pattern with concrete, type-safe schema definitions.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SchemaLoader(Protocol):
    """Protocol for loading schema definitions from various sources."""

    def load(self, schema_name: str, version: str = "1.0.0") -> dict[str, Any]:
        """Load a schema definition by name and version.

        Args:
            schema_name: Name of the schema to load
            version: Version of the schema to load

        Returns:
            The schema definition as a dictionary

        Raises:
            SchemaLoadError: If schema cannot be loaded
        """
        ...


class JsonSchemaLoader:
    """Loads schemas from local JSON files with caching."""

    def __init__(self) -> None:
        """Initialize with empty cache."""
        self._cache: dict[str, dict[str, Any]] = {}

    def load(self, schema_name: str, version: str = "1.0.0") -> dict[str, Any]:
        """Load JSON schema from file with caching.

        Args:
            schema_name: Name of the schema to load
            version: Version of the schema to load

        Returns:
            The JSON schema as a dictionary

        Raises:
            FileNotFoundError: If schema file doesn't exist
            SchemaLoadError: If schema file cannot be parsed
        """
        # Create cache key with version
        cache_key = f"{schema_name}:{version}"

        # Return cached version if available
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Try versioned and fallback locations for schema files
        schema_paths = [
            # Versioned paths (preferred)
            Path("src/wct/schemas/json_schemas")
            / schema_name
            / version
            / f"{schema_name}.json",
            Path("./src/wct/schemas/json_schemas")
            / schema_name
            / version
            / f"{schema_name}.json",
            Path(__file__).parent
            / "json_schemas"
            / schema_name
            / version
            / f"{schema_name}.json",
            # Fallback to old locations for backward compatibility
            Path("src/wct/schemas") / f"{schema_name}.json",
            Path("./src/wct/schemas") / f"{schema_name}.json",
            Path(__file__).parent / f"{schema_name}.json",
        ]

        for schema_path in schema_paths:
            if schema_path.exists():
                try:
                    with open(schema_path) as f:
                        schema_data = json.load(f)

                    # Validate that the schema version matches the requested version
                    if "version" in schema_data and schema_data["version"] != version:
                        raise SchemaLoadError(
                            f"Schema version mismatch: expected '{version}', found '{schema_data['version']}' in '{schema_path}'"
                        )

                    # Cache the loaded schema with versioned key
                    self._cache[cache_key] = schema_data
                    return schema_data
                except json.JSONDecodeError as e:
                    raise SchemaLoadError(
                        f"Invalid JSON in schema file '{schema_path}': {e}"
                    ) from e
                except OSError as e:
                    raise SchemaLoadError(
                        f"Cannot read schema file '{schema_path}': {e}"
                    ) from e

        raise FileNotFoundError(
            f"Schema file for '{schema_name}' version '{version}' not found in any of: {schema_paths}"
        )


class SchemaLoadError(Exception):
    """Raised when schema files cannot be loaded or parsed."""

    pass


@dataclass(frozen=True, slots=True)
class Schema(ABC):
    """Base class for all WCT schemas.

    Each concrete schema represents a strongly typed data structure
    and provides its own name, version, and schema definition.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique identifier for this schema."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Return the version for this schema."""

    @property
    @abstractmethod
    def schema(self) -> dict[str, Any]:
        """Return the JSON schema definition for validation.

        Design decision: Returns dict[str, Any] to maintain compatibility
        with the jsonschema library and existing validation patterns.
        Future enhancement could introduce strongly typed JSON Schema
        representations if needed.
        """
