"""Base classes for Waivern Compliance Framework schemas.

This module provides the foundation for strongly typed schemas with unified interface.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, override, runtime_checkable


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
    """Loads schemas from local JSON files with caching.

    This loader can be configured with custom search paths, making it flexible
    for different project structures. If no paths are provided, it uses sensible
    defaults relative to the loader's location.
    """

    def __init__(self, search_paths: list[Path] | None = None) -> None:
        """Initialize with empty cache and optional search paths.

        Args:
            search_paths: Optional list of base directories to search for schemas.
                         If None, uses default paths relative to this file's location.

        """
        self._cache: dict[str, dict[str, Any]] = {}
        self._custom_search_paths = search_paths

    def _generate_schema_paths(self, schema_name: str, version: str) -> list[Path]:
        """Generate list of paths to search for schema files.

        Args:
            schema_name: Name of the schema
            version: Version of the schema

        Returns:
            List of paths to try in order

        """
        if self._custom_search_paths:
            # Use custom search paths provided by caller
            schema_paths: list[Path] = []
            for base_path in self._custom_search_paths:
                # Try versioned path first
                schema_paths.append(
                    base_path / schema_name / version / f"{schema_name}.json"
                )
                # Then try direct path
                schema_paths.append(base_path / f"{schema_name}.json")
            return schema_paths
        else:
            # Use default WCT monorepo paths
            return [
                # Versioned paths (preferred)
                Path("apps/wct/src/wct/schemas/json_schemas")
                / schema_name
                / version
                / f"{schema_name}.json",
                Path("./apps/wct/src/wct/schemas/json_schemas")
                / schema_name
                / version
                / f"{schema_name}.json",
                # Non-versioned fallback
                Path("apps/wct/src/wct/schemas") / f"{schema_name}.json",
                Path("./apps/wct/src/wct/schemas") / f"{schema_name}.json",
            ]

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

        # Generate search paths based on configuration
        schema_paths = self._generate_schema_paths(schema_name, version)

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


@dataclass(frozen=True, slots=True, eq=False)
class Schema(ABC):
    """Base class for all Waivern Compliance Framework schemas.

    Each concrete schema represents a strongly typed data structure
    and provides its own name, version, and schema definition.

    Schema comparison is now type-based rather than name/version based
    for better type safety and performance.
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

    @override
    def __eq__(self, other: object) -> bool:
        """Compare schemas based on their concrete type.

        This enables type-based schema comparison instead of name/version
        comparison for better type safety and performance.
        """
        return type(other) is type(self)

    @override
    def __hash__(self) -> int:
        """Hash based on schema type for use in sets and dictionaries."""
        return hash(type(self))
