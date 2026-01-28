"""Async ArtifactStore interface with run_id scoping.

This module defines the abstract base class for persistent artifact stores.
All implementations are scoped to a specific run_id, enabling:
- Run isolation (each run has its own storage namespace)
- Resume capability (artifacts persist across process restarts)
- Audit trail (artifacts can be retained for compliance)
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from waivern_core.message import Message


class ArtifactStore(ABC):
    """Abstract base class for async artifact store implementations.

    All implementations are scoped to a specific run_id, passed at construction.
    Keys are relative to the run - the same key in different runs refers to
    different artifacts.

    Supports multiple backends: local filesystem, remote HTTP, in-memory (testing).

    Key format supports hierarchical paths (e.g., 'artifacts/findings',
    'llm_cache/abc123') for organising different artifact types within a run.
    """

    def __init__(self, run_id: str) -> None:
        """Initialise artifact store scoped to a specific run.

        Args:
            run_id: Unique identifier for the run. All operations are scoped
                to this run's namespace.

        """
        self._run_id = run_id

    @property
    def run_id(self) -> str:
        """The run ID this store is scoped to."""
        return self._run_id

    @abstractmethod
    async def save(self, key: str, message: Message) -> None:
        """Store artifact by key.

        Uses upsert semantics - if the key already exists, it is overwritten.

        Args:
            key: Storage key, supports hierarchical paths
                (e.g., 'artifacts/findings', 'llm_cache/abc123').
            message: The artifact data to store.

        """
        ...

    @abstractmethod
    async def get(self, key: str) -> Message:
        """Retrieve artifact by key.

        Args:
            key: Storage key to retrieve.

        Returns:
            The stored artifact.

        Raises:
            ArtifactNotFoundError: If artifact with key does not exist.

        """
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if artifact exists.

        Args:
            key: Storage key to check.

        Returns:
            True if artifact exists, False otherwise.

        """
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete artifact by key.

        No-op if the key does not exist.

        Args:
            key: Storage key to delete.

        """
        ...

    @abstractmethod
    async def list_keys(self, prefix: str = "") -> list[str]:
        """List all keys in this run, optionally filtered by prefix.

        Args:
            prefix: Optional prefix to filter keys. Empty string returns all keys.

        Returns:
            List of matching keys.

        """
        ...

    @abstractmethod
    async def clear(self) -> None:
        """Remove all artifacts for this run.

        This deletes all stored artifacts within the run's namespace.
        """
        ...
