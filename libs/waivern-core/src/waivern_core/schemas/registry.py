"""Schema registry for Waivern Compliance Framework.

This module provides centralised management of schema search paths and loader instances,
enabling packages to contribute their own schemas without modifying waivern-core code.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar, TypedDict

from waivern_core.schemas.loader import JsonSchemaLoader


class SchemaRegistryState(TypedDict):
    """State snapshot for SchemaRegistry.

    Used for test isolation - captures and restores registry state
    to prevent test pollution.
    """

    search_paths: list[Path]
    initialised: bool


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
    def snapshot_state(cls) -> SchemaRegistryState:
        """Capture current SchemaRegistry state for later restoration.

        This is primarily used for test isolation - save state before tests,
        restore after tests to prevent global state pollution.

        Returns:
            State dictionary containing all mutable registry state

        """
        return {
            "search_paths": cls._search_paths.copy(),
            "initialised": cls._initialised,
            # Note: _loader is not captured - it will be recreated as needed
        }

    @classmethod
    def restore_state(cls, state: SchemaRegistryState) -> None:
        """Restore SchemaRegistry state from a previously captured snapshot.

        This is primarily used for test isolation - restore state after tests
        to ensure tests don't pollute global state.

        Args:
            state: State dictionary from snapshot_state()

        """
        cls._search_paths = state["search_paths"].copy()
        cls._initialised = state["initialised"]
        cls._loader = None  # Force recreation with restored paths
