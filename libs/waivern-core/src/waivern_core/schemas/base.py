"""Base classes for Waivern Compliance Framework schemas.

This module provides the foundation for strongly typed schemas with unified interface.
"""

from __future__ import annotations

import json
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
    for different project structures. If no paths are provided, it searches
    package-relative paths (json_schemas/ directory alongside this file).

    The loader caches schemas after first load to improve performance.

    Design note: Each schema explicitly provides custom search_paths for clarity
    and debuggability. This explicit approach was chosen over alternatives like
    autodiscovery or automatic path detection. See ADR-0001 for detailed rationale.
    """

    def __init__(self, search_paths: list[Path] | None = None) -> None:
        """Initialize with empty cache and optional search paths.

        Args:
            search_paths: Optional list of base directories to search for schemas.
                         If provided, ONLY these paths are searched (overrides defaults).
                         If None, uses package-relative path (json_schemas/ alongside this file).

        """
        self._cache: dict[str, dict[str, Any]] = {}
        self._custom_search_paths = search_paths

    def _generate_schema_paths(self, schema_name: str, version: str) -> list[Path]:
        """Generate list of paths to search for schema files.

        Search order:
        1. Custom search paths (if provided)
        2. Package-relative paths (json_schemas/ directory alongside this file)

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
                schema_paths.append(
                    base_path / schema_name / version / f"{schema_name}.json"
                )
            return schema_paths
        else:
            # Default search paths
            # Package-relative path (where this base.py file lives)
            package_base = Path(__file__).parent / "json_schemas"

            return [
                package_base / schema_name / version / f"{schema_name}.json",
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


class Schema:
    """Generic schema class for all Waivern Compliance Framework schemas.

    Schema objects are lightweight descriptors instantiated with name and version.
    JSON schema files are loaded lazily only when actually needed.

    Schema loading uses fixed conventional search paths. All schemas must be
    placed in one of these conventional locations.
    """

    # Fixed conventional search paths - schemas must be in one of these locations
    _SEARCH_PATHS: list[Path] = [
        Path(__file__).parent / "json_schemas",  # waivern-core/schemas/json_schemas/
        # Additional conventional paths can be added here as framework grows
    ]

    # Shared singleton loader for caching across all Schema instances
    _loader: JsonSchemaLoader | None = None

    @classmethod
    def _get_loader(cls) -> JsonSchemaLoader:
        """Get or create the shared singleton loader."""
        if cls._loader is None:
            cls._loader = JsonSchemaLoader(search_paths=cls._SEARCH_PATHS)
        return cls._loader

    def __init__(self, name: str, version: str) -> None:
        """Initialise schema descriptor (does not load JSON file).

        Args:
            name: Schema name (e.g., "standard_input")
            version: Schema version (e.g., "1.0.0")

        """
        self._name = name
        self._version = version
        self._schema_def: dict[str, Any] | None = None  # Lazy - loaded on demand

    @property
    def name(self) -> str:
        """Return the unique identifier for this schema."""
        return self._name

    @property
    def version(self) -> str:
        """Return the version for this schema."""
        return self._version

    @property
    def schema(self) -> dict[str, Any]:
        """Get JSON schema definition, loading from file if needed.

        Returns:
            The JSON schema definition as a dictionary

        Raises:
            SchemaLoadError: If schema file cannot be loaded or validation fails
            FileNotFoundError: If schema JSON file doesn't exist

        """
        if self._schema_def is None:
            # Lazy load using shared singleton loader (for cache efficiency)
            loader = self._get_loader()
            self._schema_def = loader.load(self._name, self._version)

            # Validate JSON version matches parameter (name is implied by directory)
            if self._schema_def.get("version") != self._version:
                raise SchemaLoadError(
                    f"Schema version mismatch: expected '{self._version}', "
                    f"found '{self._schema_def.get('version')}'"
                )

        return self._schema_def

    @override
    def __eq__(self, other: object) -> bool:
        """Compare schemas based on (name, version) tuple.

        This enables version-aware schema comparison for multi-version support.
        """
        if not isinstance(other, Schema):
            return False
        return self.name == other.name and self.version == other.version

    @override
    def __hash__(self) -> int:
        """Hash based on (name, version) tuple for use in sets and dictionaries."""
        return hash((self.name, self.version))

    @override
    def __repr__(self) -> str:
        """Return string representation of schema."""
        return f"Schema(name='{self.name}', version='{self.version}')"
