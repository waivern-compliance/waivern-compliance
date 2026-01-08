"""In-memory artifact store implementation."""

from __future__ import annotations

import threading
from typing import override

from waivern_core.message import Message

from waivern_artifact_store.base import ArtifactStore
from waivern_artifact_store.errors import ArtifactNotFoundError


class InMemoryArtifactStore(ArtifactStore):
    """In-memory artifact store implementation using dict-based storage.

    This implementation stores artifacts in memory using a dictionary.
    Thread-safe for concurrent access via threading.Lock.

    Attributes:
        _storage: Dictionary mapping step_id to Message
        _lock: Lock for thread-safe operations

    """

    def __init__(self) -> None:
        """Initialise in-memory artifact store."""
        self._storage: dict[str, Message] = {}
        self._lock = threading.Lock()

    @override
    def save(self, step_id: str, message: Message) -> None:
        """Store artifact from completed step.

        Args:
            step_id: Unique identifier for the step that produced this artifact
            message: The artifact data to store

        """
        with self._lock:
            self._storage[step_id] = message

    @override
    def get(self, step_id: str) -> Message:
        """Retrieve artifact for downstream step.

        Args:
            step_id: Unique identifier for the step artifact to retrieve

        Returns:
            The stored artifact

        Raises:
            ArtifactNotFoundError: If artifact with step_id does not exist

        """
        with self._lock:
            if step_id not in self._storage:
                raise ArtifactNotFoundError(
                    f"Artifact '{step_id}' not found. "
                    f"Ensure the artifact exists in the runbook and completed successfully."
                )
            return self._storage[step_id]

    @override
    def exists(self, step_id: str) -> bool:
        """Check if artifact exists in storage.

        Args:
            step_id: Unique identifier for the step artifact

        Returns:
            True if artifact exists, False otherwise

        """
        with self._lock:
            return step_id in self._storage

    @override
    def clear(self) -> None:
        """Remove all artifacts from storage.

        This is called at the end of pipeline execution to clean up resources.
        """
        with self._lock:
            self._storage.clear()

    @override
    def list_artifacts(self) -> list[str]:
        """Return list of all stored artifact IDs.

        Returns:
            List of artifact IDs currently in storage.

        """
        with self._lock:
            return list(self._storage.keys())
