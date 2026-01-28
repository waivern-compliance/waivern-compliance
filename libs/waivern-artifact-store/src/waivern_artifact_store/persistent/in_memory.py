"""Async in-memory artifact store implementation.

Provides an in-memory implementation of the ArtifactStore interface
for testing without filesystem dependencies.
"""

from __future__ import annotations

from typing import override

from waivern_core.message import Message

from waivern_artifact_store.errors import ArtifactNotFoundError
from waivern_artifact_store.persistent.base import ArtifactStore


class AsyncInMemoryStore(ArtifactStore):
    """In-memory artifact store for testing.

    Uses a simple dict for storage. No thread safety is needed
    since asyncio runs in a single thread.

    This store implements the same `_system` prefix filtering as
    LocalFilesystemStore for behavioural consistency.
    """

    def __init__(self, run_id: str) -> None:
        """Initialise in-memory store.

        Args:
            run_id: Unique identifier for the run.

        """
        super().__init__(run_id)
        self._storage: dict[str, Message] = {}

    @override
    async def save(self, key: str, message: Message) -> None:
        """Store artifact by key.

        Uses upsert semantics - overwrites if key already exists.
        """
        self._storage[key] = message

    @override
    async def get(self, key: str) -> Message:
        """Retrieve artifact by key.

        Raises:
            ArtifactNotFoundError: If artifact with key does not exist.

        """
        if key not in self._storage:
            raise ArtifactNotFoundError(
                f"Artifact '{key}' not found in run '{self._run_id}'."
            )
        return self._storage[key]

    @override
    async def exists(self, key: str) -> bool:
        """Check if artifact exists."""
        return key in self._storage

    @override
    async def delete(self, key: str) -> None:
        """Delete artifact by key.

        No-op if the key does not exist.
        """
        self._storage.pop(key, None)

    # Reserved prefix for system metadata (excluded from list_keys)
    _SYSTEM_PREFIX = "_system"

    @override
    async def list_keys(self, prefix: str = "") -> list[str]:
        """List all keys, optionally filtered by prefix.

        System files under '_system/' are excluded for consistency
        with LocalFilesystemStore behaviour.
        """
        keys: list[str] = []
        for key in self._storage:
            # Skip system files
            if key.startswith(self._SYSTEM_PREFIX):
                continue
            # Filter by prefix if provided
            if not prefix or key.startswith(prefix):
                keys.append(key)
        return keys

    @override
    async def clear(self) -> None:
        """Remove all artifacts for this run."""
        self._storage.clear()
