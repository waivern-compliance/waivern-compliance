"""Base classes for Waivern Compliance Framework schemas.

This module provides the foundation for strongly typed schemas with unified interface.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, ClassVar, Protocol, override, runtime_checkable


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
        self._cache: dict[tuple[str, str], dict[str, Any]] = {}
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
        # Create cache key using tuple for type safety
        cache_key = (schema_name, version)

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

                    # Cache the loaded schema using tuple key
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


class SchemaRegistry:
    """Registry for managing schema infrastructure.

    Provides centralised management of schema search paths and loader instances.
    This enables packages to contribute their own schemas without modifying
    waivern-core code (Open/Closed Principle).

    The registry maintains default search paths, allows additional paths to be
    registered at runtime, and provides a shared singleton loader for efficiency.
    """

    # Class-level storage for search paths (shared across all instances)
    _search_paths: ClassVar[list[Path]] = []
    _initialised: ClassVar[bool] = False

    # Shared singleton loader for caching across all Schema instances
    _loader: ClassVar[JsonSchemaLoader | None] = None

    @classmethod
    def _ensure_initialised(cls) -> None:
        """Ensure default search paths are registered (called once)."""
        if not cls._initialised:
            # Register default waivern-core schema location
            default_path = Path(__file__).parent / "json_schemas"
            cls._search_paths.append(default_path)
            cls._initialised = True

    @classmethod
    def register_search_path(cls, path: Path) -> None:
        """Register an additional search path for schemas.

        Args:
            path: Base directory containing schema files
                 (expects subdirectories: {schema_name}/{version}/)

        Example:
            >>> from pathlib import Path
            >>> SchemaRegistry.register_search_path(
            ...     Path(__file__).parent / "my_schemas"
            ... )

        Note:
            Invalidates the singleton loader cache, forcing recreation with new paths.

        """
        cls._ensure_initialised()
        if path not in cls._search_paths:
            cls._search_paths.append(path)
            # Invalidate loader cache when paths change
            cls._loader = None

    @classmethod
    def get_search_paths(cls) -> list[Path]:
        """Get all registered search paths.

        Returns:
            List of search paths in registration order

        """
        cls._ensure_initialised()
        return cls._search_paths.copy()

    @classmethod
    def get_loader(cls) -> JsonSchemaLoader:
        """Get or create the shared singleton loader.

        Returns:
            Shared JsonSchemaLoader instance configured with registered paths

        """
        if cls._loader is None:
            search_paths = cls.get_search_paths()
            cls._loader = JsonSchemaLoader(search_paths=search_paths)
        return cls._loader

    @classmethod
    def clear_search_paths(cls) -> None:
        """Clear all registered search paths (primarily for testing).

        Note:
            Also clears the singleton loader cache.

        """
        cls._search_paths.clear()
        cls._initialised = False
        cls._loader = None

    @classmethod
    def snapshot_state(cls) -> dict[str, Any]:
        """Capture current SchemaRegistry state for later restoration.

        This is primarily used for test isolation - save state before tests,
        restore after tests to prevent global state pollution.

        Returns:
            Dictionary containing all mutable state

        """
        return {
            "search_paths": cls._search_paths.copy(),
            "initialised": cls._initialised,
            # Note: _loader is not captured - it will be recreated as needed
        }

    @classmethod
    def restore_state(cls, state: dict[str, Any]) -> None:
        """Restore SchemaRegistry state from a previously captured snapshot.

        This is primarily used for test isolation - restore state after tests
        to ensure tests don't pollute global state.

        Args:
            state: State dictionary from snapshot_state()

        """
        cls._search_paths = state["search_paths"].copy()
        cls._initialised = state["initialised"]
        cls._loader = None  # Force recreation with restored paths


class Schema:
    """Generic schema class for all Waivern Compliance Framework schemas.

    Schema objects are lightweight descriptors instantiated with name and version.
    JSON schema files are loaded lazily only when actually needed.

    Schema loading uses the shared loader from SchemaRegistry. Custom loaders can
    be injected for testing or alternative schema sources (dependency injection).
    """

    def __init__(
        self, name: str, version: str, loader: JsonSchemaLoader | None = None
    ) -> None:
        """Initialise schema descriptor (does not load JSON file).

        Args:
            name: Schema name (e.g., "standard_input")
            version: Schema version (e.g., "1.0.0")
            loader: Optional custom loader. If None, uses shared singleton loader
                   from SchemaRegistry (dependency injection)

        """
        self._name = name
        self._version = version
        self._loader = loader  # Instance-specific loader (or None for shared)
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
            # Use instance-specific loader if provided, otherwise shared registry loader
            # Loader validates version correctness, so no additional validation needed
            loader = (
                self._loader
                if self._loader is not None
                else SchemaRegistry.get_loader()
            )
            self._schema_def = loader.load(self._name, self._version)

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

    @override
    def __getstate__(self) -> dict[str, str]:
        """Return serialisable state (name and version only).

        The loader and cached schema definition are runtime infrastructure
        and do not need to be persisted.
        """
        return {"name": self._name, "version": self._version}

    def __setstate__(self, state: dict[str, str]) -> None:
        """Restore from serialised state."""
        self._name = state["name"]
        self._version = state["version"]
        self._loader = None
        self._schema_def = None

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,  # noqa: ANN401
        handler: Any,  # noqa: ANN401
    ) -> Any:  # noqa: ANN401
        """Enable Pydantic serialisation using Python native __getstate__/__setstate__.

        NOTE: Lint ignores are intentional:
        - ANN401 (Any types): Pydantic is an optional dependency, so we cannot import
          the specific types (GetCoreSchemaHandler, CoreSchema) at module level.
        - PLC0415 (import not at top-level): pydantic_core import is inside the method
          to avoid making Pydantic a required dependency of waivern-core.
        """
        from pydantic_core import core_schema  # noqa: PLC0415

        def validate_schema(value: Any) -> Schema:  # noqa: ANN401
            if isinstance(value, Schema):
                return value
            if isinstance(value, dict):
                instance = object.__new__(Schema)
                state: dict[str, str] = {
                    "name": value["name"],
                    "version": value["version"],
                }
                instance.__setstate__(state)
                return instance
            raise ValueError(f"Cannot convert {type(value)} to Schema")

        def serialize_schema(value: Schema) -> dict[str, str]:
            return value.__getstate__()

        return core_schema.no_info_plain_validator_function(
            validate_schema,
            serialization=core_schema.plain_serializer_function_ser_schema(
                serialize_schema,
                info_arg=False,
            ),
        )
