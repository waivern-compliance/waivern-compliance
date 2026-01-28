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

    Stateless singleton that stores artifacts keyed by (run_id, key).
    No thread safety is needed since asyncio runs in a single thread.

    This store implements the same `_system` prefix filtering as
    LocalFilesystemStore for behavioural consistency.
    """

    # Reserved prefix for system metadata (excluded from list_keys)
    _SYSTEM_PREFIX = "_system"

    def __init__(self) -> None:
        """Initialise in-memory store."""
        # Storage: run_id -> key -> Message
        self._storage: dict[str, dict[str, Message]] = {}

    def _get_run_storage(self, run_id: str) -> dict[str, Message]:
        """Get or create storage dict for a run."""
        if run_id not in self._storage:
            self._storage[run_id] = {}
        return self._storage[run_id]

    @override
    async def save(self, run_id: str, key: str, message: Message) -> None:
        """Store artifact by key.

        Uses upsert semantics - overwrites if key already exists.
        """
        self._get_run_storage(run_id)[key] = message

    @override
    async def get(self, run_id: str, key: str) -> Message:
        """Retrieve artifact by key.

        Raises:
            ArtifactNotFoundError: If artifact with key does not exist.

        """
        run_storage = self._get_run_storage(run_id)
        if key not in run_storage:
            raise ArtifactNotFoundError(
                f"Artifact '{key}' not found in run '{run_id}'."
            )
        return run_storage[key]

    @override
    async def exists(self, run_id: str, key: str) -> bool:
        """Check if artifact exists."""
        return key in self._get_run_storage(run_id)

    @override
    async def delete(self, run_id: str, key: str) -> None:
        """Delete artifact by key.

        No-op if the key does not exist.
        """
        self._get_run_storage(run_id).pop(key, None)

    @override
    async def list_keys(self, run_id: str, prefix: str = "") -> list[str]:
        """List all keys for a run, optionally filtered by prefix.

        System files under '_system/' are excluded for consistency
        with LocalFilesystemStore behaviour.
        """
        keys: list[str] = []
        for key in self._get_run_storage(run_id):
            # Skip system files
            if key.startswith(self._SYSTEM_PREFIX):
                continue
            # Filter by prefix if provided
            if not prefix or key.startswith(prefix):
                keys.append(key)
        return keys

    @override
    async def clear(self, run_id: str) -> None:
        """Remove all artifacts for a run."""
        if run_id in self._storage:
            self._storage[run_id].clear()
