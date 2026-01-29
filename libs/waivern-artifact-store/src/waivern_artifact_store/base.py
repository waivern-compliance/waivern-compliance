"""Async ArtifactStore interface (stateless, run_id per operation).

This module defines the abstract base class for persistent artifact stores.
The interface is stateless - run_id is passed to each operation, enabling:
- Singleton stores (one instance shared across all runs)
- Standard DI patterns (factory.create() takes no parameters)
- Resource sharing (HTTP clients, connection pools held by store)
- Run isolation (run_id parameter scopes each operation)
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from waivern_core import JsonValue
from waivern_core.message import Message


class ArtifactStore(ABC):
    """Abstract base class for async artifact store implementations.

    Stateless interface where run_id is passed to each operation.
    This enables singleton stores compatible with standard DI patterns.

    Supports multiple backends: local filesystem, remote HTTP, in-memory (testing).

    Key format supports hierarchical paths (e.g., 'artifacts/findings',
    'llm_cache/abc123') for organising different artifact types within a run.
    """

    @abstractmethod
    async def save(self, run_id: str, key: str, message: Message) -> None:
        """Store artifact by key.

        Uses upsert semantics - if the key already exists, it is overwritten.

        Args:
            run_id: Unique identifier for the run.
            key: Storage key, supports hierarchical paths
                (e.g., 'artifacts/findings', 'llm_cache/abc123').
            message: The artifact data to store.

        """
        ...

    @abstractmethod
    async def get(self, run_id: str, key: str) -> Message:
        """Retrieve artifact by key.

        Args:
            run_id: Unique identifier for the run.
            key: Storage key to retrieve.

        Returns:
            The stored artifact.

        Raises:
            ArtifactNotFoundError: If artifact with key does not exist.

        """
        ...

    @abstractmethod
    async def exists(self, run_id: str, key: str) -> bool:
        """Check if artifact exists.

        Args:
            run_id: Unique identifier for the run.
            key: Storage key to check.

        Returns:
            True if artifact exists, False otherwise.

        """
        ...

    @abstractmethod
    async def delete(self, run_id: str, key: str) -> None:
        """Delete artifact by key.

        No-op if the key does not exist.

        Args:
            run_id: Unique identifier for the run.
            key: Storage key to delete.

        """
        ...

    @abstractmethod
    async def list_keys(self, run_id: str, prefix: str = "") -> list[str]:
        """List all keys for a run, optionally filtered by prefix.

        Args:
            run_id: Unique identifier for the run.
            prefix: Optional prefix to filter keys. Empty string returns all keys.

        Returns:
            List of matching keys.

        """
        ...

    @abstractmethod
    async def clear(self, run_id: str) -> None:
        """Remove all artifacts for a run.

        Args:
            run_id: Unique identifier for the run.

        """
        ...

    # -------------------------------------------------------------------------
    # JSON Storage (for system metadata like execution state)
    # -------------------------------------------------------------------------

    @abstractmethod
    async def save_json(
        self, run_id: str, key: str, data: dict[str, JsonValue]
    ) -> None:
        """Store raw JSON data by key (for system metadata).

        Uses upsert semantics - if the key already exists, it is overwritten.

        Args:
            run_id: Unique identifier for the run.
            key: Storage key, supports hierarchical paths
                (e.g., '_system/state', '_system/run').
            data: The dictionary data to store.

        """
        ...

    @abstractmethod
    async def get_json(self, run_id: str, key: str) -> dict[str, JsonValue]:
        """Retrieve raw JSON data by key.

        Args:
            run_id: Unique identifier for the run.
            key: Storage key to retrieve.

        Returns:
            The stored dictionary data.

        Raises:
            ArtifactNotFoundError: If data with key does not exist.

        """
        ...
