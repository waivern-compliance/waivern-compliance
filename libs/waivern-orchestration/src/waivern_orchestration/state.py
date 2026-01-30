"""Execution state model for tracking run progress.

ExecutionState tracks which artifacts have completed, failed, or are pending
during a DAG execution. It supports persistence to ArtifactStore for resume
capability.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Self

from pydantic import BaseModel, Field
from waivern_artifact_store.base import ArtifactStore


class ExecutionState(BaseModel):
    """Tracks execution progress for a run.

    Each artifact can be in one of four states:
    - not_started: Waiting to be executed
    - completed: Successfully finished
    - failed: Execution failed
    - skipped: Skipped due to upstream failure

    State transitions are one-way: not_started → {completed, failed, skipped}
    """

    run_id: str
    """Unique identifier for this run."""

    completed: set[str] = Field(default_factory=set)
    """Artifact IDs that completed successfully."""

    not_started: set[str] = Field(default_factory=set)
    """Artifact IDs not yet started."""

    failed: set[str] = Field(default_factory=set)
    """Artifact IDs that failed during execution."""

    skipped: set[str] = Field(default_factory=set)
    """Artifact IDs skipped due to upstream failure."""

    last_checkpoint: datetime = Field(default_factory=lambda: datetime.now(UTC))
    """Last state save timestamp (UTC)."""

    @classmethod
    def fresh(cls, run_id: str, artifact_ids: set[str]) -> Self:
        """Create initial state with all artifacts in not_started.

        Args:
            run_id: Unique identifier for this run.
            artifact_ids: Set of artifact IDs to track.

        Returns:
            New ExecutionState with all artifacts pending.

        """
        return cls(
            run_id=run_id,
            completed=set(),
            not_started=artifact_ids.copy(),
            failed=set(),
            skipped=set(),
            last_checkpoint=datetime.now(UTC),
        )

    def mark_completed(self, artifact_id: str) -> None:
        """Move artifact from not_started to completed.

        No-op if artifact is not in not_started (idempotent, no pollution).

        Note: Currently only checks not_started. If intermediate states are added
        in the future (e.g., 'running'), this method should check those as well.

        Args:
            artifact_id: The artifact ID to mark as completed.

        """
        if artifact_id not in self.not_started:
            return
        self.not_started.discard(artifact_id)
        self.completed.add(artifact_id)
        self.last_checkpoint = datetime.now(UTC)

    def mark_failed(self, artifact_id: str) -> None:
        """Move artifact from not_started to failed.

        No-op if artifact is not in not_started (idempotent, no pollution).

        Note: Currently only checks not_started. If intermediate states are added
        in the future (e.g., 'running'), this method should check those as well.

        Args:
            artifact_id: The artifact ID to mark as failed.

        """
        if artifact_id not in self.not_started:
            return
        self.not_started.discard(artifact_id)
        self.failed.add(artifact_id)
        self.last_checkpoint = datetime.now(UTC)

    def mark_skipped(self, artifact_ids: set[str]) -> None:
        """Move multiple artifacts from not_started to skipped.

        Only moves artifacts that are currently in not_started (no pollution).
        Used when upstream artifacts fail and dependents cannot run.

        Note: Currently only checks not_started. If intermediate states are added
        in the future (e.g., 'running'), this method should check those as well.

        Args:
            artifact_ids: Set of artifact IDs to mark as skipped.

        """
        to_skip = artifact_ids & self.not_started
        self.not_started -= to_skip
        self.skipped |= to_skip
        if to_skip:
            self.last_checkpoint = datetime.now(UTC)

    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------

    @classmethod
    async def load(cls, store: ArtifactStore, run_id: str) -> Self:
        """Load state from store.

        Args:
            store: The artifact store to load from.
            run_id: The run identifier.

        Returns:
            Loaded ExecutionState.

        Raises:
            ArtifactNotFoundError: If state does not exist for this run.

        """
        data = await store.load_execution_state(run_id)
        return cls.model_validate(data)

    async def save(self, store: ArtifactStore) -> None:
        """Persist state to store.

        Updates last_checkpoint before saving.

        Args:
            store: The artifact store to save to.

        """
        self.last_checkpoint = datetime.now(UTC)
        data = self.model_dump(mode="json")
        await store.save_execution_state(self.run_id, data)
