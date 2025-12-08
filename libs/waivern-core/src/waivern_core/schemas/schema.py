"""Schema class for Waivern Compliance Framework.

This module provides the Schema class - a lightweight descriptor for schema
identification with lazy loading of JSON schema definitions.
"""

from __future__ import annotations

from typing import Any, override

from waivern_core.schemas.loader import JsonSchemaLoader
from waivern_core.schemas.registry import SchemaRegistry


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
