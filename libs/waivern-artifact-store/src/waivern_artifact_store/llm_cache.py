"""LLM Cache Protocol for artifact store implementations.

This module defines the LLMCache protocol for LLM response caching operations.
Artifact store implementations (InMemoryArtifactStore, FilesystemArtifactStore)
implement this protocol to provide cache storage alongside artifact storage.
"""

from __future__ import annotations

from typing import Protocol

from waivern_core import JsonValue


class LLMCache(Protocol):
    """Protocol for LLM response caching operations.

    Provides key-value storage for cache entries, scoped by run_id.
    Entries are stored as JSON-serializable dictionaries.

    Implementations: AsyncInMemoryStore, LocalFilesystemStore
    """

    async def cache_get(self, run_id: str, key: str) -> dict[str, JsonValue] | None:
        """Retrieve a cache entry by key.

        Args:
            run_id: Unique identifier for the run.
            key: Cache key (typically a prompt hash).

        Returns:
            The cached entry, or None if not found.

        """
        ...

    async def cache_set(
        self, run_id: str, key: str, entry: dict[str, JsonValue]
    ) -> None:
        """Store a cache entry.

        Upsert semantics — overwrites if key exists.

        Args:
            run_id: Unique identifier for the run.
            key: Cache key (typically a prompt hash).
            entry: The cache entry data.

        """
        ...

    async def cache_delete(self, run_id: str, key: str) -> None:
        """Delete a cache entry by key.

        No-op if entry does not exist.

        Args:
            run_id: Unique identifier for the run.
            key: Cache key to delete.

        """
        ...

    async def cache_clear(self, run_id: str) -> None:
        """Delete all cache entries for a run.

        Called after LLMService.complete() returns successfully.

        Args:
            run_id: Unique identifier for the run.

        """
        ...
