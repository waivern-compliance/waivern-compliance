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

    Each artifact can be in one of five states:
    - not_started: Waiting to be executed
    - pending: Dispatched but awaiting results (e.g., batch job submitted)
    - completed: Successfully finished
    - failed: Execution failed
    - skipped: Skipped due to upstream failure

    State transitions:
    - not_started → {pending, completed, failed, skipped}
    - pending → {completed, failed, skipped}
    - completed, failed, skipped → terminal (no outgoing transitions)
    """

    run_id: str
    """Unique identifier for this run."""

    completed: set[str] = Field(default_factory=set)
    """Artifact IDs that completed successfully."""

    not_started: set[str] = Field(default_factory=set)
    """Artifact IDs not yet started."""

    pending: set[str] = Field(default_factory=set)
    """Artifact IDs dispatched but awaiting results."""

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
            New ExecutionState with all artifacts in not_started.

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
        """Move artifact from not_started or pending to completed.

        No-op if artifact is not in not_started or pending (idempotent, no pollution).

        Args:
            artifact_id: The artifact ID to mark as completed.

        """
        if artifact_id in self.not_started:
            self.not_started.discard(artifact_id)
        elif artifact_id in self.pending:
            self.pending.discard(artifact_id)
        else:
            return
        self.completed.add(artifact_id)
        self.last_checkpoint = datetime.now(UTC)

    def mark_pending(self, artifact_id: str) -> None:
        """Move artifact from not_started to pending.

        No-op if artifact is not in not_started (idempotent, no pollution).

        Args:
            artifact_id: The artifact ID to mark as pending.

        """
        if artifact_id in self.not_started:
            self.not_started.discard(artifact_id)
        else:
            return
        self.pending.add(artifact_id)
        self.last_checkpoint = datetime.now(UTC)

    def mark_failed(self, artifact_id: str) -> None:
        """Move artifact from not_started or pending to failed.

        No-op if artifact is not in not_started or pending (idempotent, no pollution).

        Args:
            artifact_id: The artifact ID to mark as failed.

        """
        if artifact_id in self.not_started:
            self.not_started.discard(artifact_id)
        elif artifact_id in self.pending:
            self.pending.discard(artifact_id)
        else:
            return
        self.failed.add(artifact_id)
        self.last_checkpoint = datetime.now(UTC)

    def mark_skipped(self, artifact_ids: set[str]) -> None:
        """Move multiple artifacts from not_started or pending to skipped.

        Only moves artifacts that are currently in not_started or pending
        (no pollution). Used when upstream artifacts fail and dependents
        cannot run.

        Args:
            artifact_ids: Set of artifact IDs to mark as skipped.

        """
        from_not_started = artifact_ids & self.not_started
        from_pending = artifact_ids & self.pending
        to_skip = from_not_started | from_pending
        self.not_started -= from_not_started
        self.pending -= from_pending
        self.skipped |= to_skip
        if to_skip:
            self.last_checkpoint = datetime.now(UTC)

    def remaining_actionable(self, all_artifact_ids: set[str]) -> set[str]:
        """Compute artifact IDs that are not in any terminal or pending state.

        Returns the set difference of all artifacts minus those that are
        completed, failed, skipped, or pending. These are the artifacts
        that have not yet been acted on.

        Args:
            all_artifact_ids: The complete set of artifact IDs in the plan.

        Returns:
            Set of artifact IDs still in not_started state.

        """
        return (
            all_artifact_ids
            - self.completed
            - self.skipped
            - self.failed
            - self.pending
        )

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
        data = await store.load_system_data(run_id, "state")
        return cls.model_validate(data)

    async def save(self, store: ArtifactStore) -> None:
        """Persist state to store.

        Updates last_checkpoint before saving.

        Args:
            store: The artifact store to save to.

        """
        self.last_checkpoint = datetime.now(UTC)
        data = self.model_dump(mode="json")
        await store.save_system_data(self.run_id, "state", data)
