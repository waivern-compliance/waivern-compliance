"""Async in-memory artifact store implementation.

Provides an in-memory implementation of the ArtifactStore interface
for testing without filesystem dependencies.
"""

from __future__ import annotations

from typing import override

from waivern_core import JsonValue
from waivern_core.message import Message

from waivern_artifact_store.base import ArtifactStore
from waivern_artifact_store.errors import ArtifactNotFoundError


class AsyncInMemoryStore(ArtifactStore):
    """In-memory artifact store for testing.

    Stateless singleton that stores artifacts keyed by (run_id, artifact_id).
    No thread safety is needed since asyncio runs in a single thread.

    Artifacts are stored separately from system metadata for clean semantics.
    """

    def __init__(self) -> None:
        """Initialise in-memory store."""
        # Artifact storage: run_id -> artifact_id -> Message
        self._artifacts: dict[str, dict[str, Message]] = {}
        # System metadata storage: run_id -> key -> dict
        self._system_data: dict[str, dict[str, dict[str, JsonValue]]] = {}

    def _get_artifact_storage(self, run_id: str) -> dict[str, Message]:
        """Get or create artifact storage dict for a run."""
        if run_id not in self._artifacts:
            self._artifacts[run_id] = {}
        return self._artifacts[run_id]

    def _get_system_storage(self, run_id: str) -> dict[str, dict[str, JsonValue]]:
        """Get or create system metadata storage dict for a run."""
        if run_id not in self._system_data:
            self._system_data[run_id] = {}
        return self._system_data[run_id]

    # ========================================================================
    # Artifact Operations
    # ========================================================================

    @override
    async def save_artifact(
        self, run_id: str, artifact_id: str, message: Message
    ) -> None:
        """Store artifact by ID."""
        self._get_artifact_storage(run_id)[artifact_id] = message

    @override
    async def get_artifact(self, run_id: str, artifact_id: str) -> Message:
        """Retrieve artifact by ID."""
        artifacts = self._get_artifact_storage(run_id)
        if artifact_id not in artifacts:
            raise ArtifactNotFoundError(
                f"Artifact '{artifact_id}' not found in run '{run_id}'."
            )
        return artifacts[artifact_id]

    @override
    async def artifact_exists(self, run_id: str, artifact_id: str) -> bool:
        """Check if artifact exists."""
        return artifact_id in self._get_artifact_storage(run_id)

    @override
    async def delete_artifact(self, run_id: str, artifact_id: str) -> None:
        """Delete artifact by ID."""
        self._get_artifact_storage(run_id).pop(artifact_id, None)

    @override
    async def list_artifacts(self, run_id: str) -> list[str]:
        """List all artifact IDs for a run."""
        return sorted(self._get_artifact_storage(run_id).keys())

    @override
    async def clear_artifacts(self, run_id: str) -> None:
        """Remove all artifacts for a run (preserves system metadata)."""
        if run_id in self._artifacts:
            self._artifacts[run_id].clear()

    # ========================================================================
    # System Metadata Operations
    # ========================================================================

    @override
    async def save_execution_state(
        self, run_id: str, state_data: dict[str, JsonValue]
    ) -> None:
        """Persist execution state."""
        self._get_system_storage(run_id)["state"] = state_data

    @override
    async def load_execution_state(self, run_id: str) -> dict[str, JsonValue]:
        """Load execution state."""
        system_data = self._get_system_storage(run_id)
        if "state" not in system_data:
            raise ArtifactNotFoundError(
                f"Execution state not found for run '{run_id}'."
            )
        return system_data["state"]

    @override
    async def save_run_metadata(
        self, run_id: str, metadata: dict[str, JsonValue]
    ) -> None:
        """Persist run metadata."""
        self._get_system_storage(run_id)["metadata"] = metadata

    @override
    async def load_run_metadata(self, run_id: str) -> dict[str, JsonValue]:
        """Load run metadata."""
        system_data = self._get_system_storage(run_id)
        if "metadata" not in system_data:
            raise ArtifactNotFoundError(f"Run metadata not found for run '{run_id}'.")
        return system_data["metadata"]

    # ========================================================================
    # Run Enumeration
    # ========================================================================

    @override
    async def list_runs(self) -> list[str]:
        """List all run IDs in the store."""
        # Combine keys from both storages (a run may exist in either or both)
        all_run_ids = set(self._artifacts.keys()) | set(self._system_data.keys())
        return sorted(all_run_ids)
