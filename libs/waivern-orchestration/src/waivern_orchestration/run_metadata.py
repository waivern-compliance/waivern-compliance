"""Run metadata model for tracking run-level information.

RunMetadata stores information about a run including its status and timestamps.
It supports persistence to ArtifactStore for resume capability.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel
from waivern_artifact_store.base import ArtifactStore

# Valid run status values
RunStatus = Literal["running", "completed", "failed", "interrupted"]


class RunMetadata(BaseModel):
    """Metadata for a single execution run.

    Tracks run-level information including:
    - Run identification (run_id, runbook_path)
    - Status (running, completed, failed, interrupted)
    - Timestamps (started_at, completed_at)
    """

    run_id: str
    """Unique identifier for this run (UUID)."""

    runbook_path: str
    """Path to the runbook file that was executed."""

    started_at: datetime
    """When the run started (UTC)."""

    completed_at: datetime | None = None
    """When the run completed (UTC). None if still running."""

    status: RunStatus = "running"
    """Current run status."""

    @classmethod
    def fresh(
        cls,
        run_id: str,
        runbook_path: Path,
    ) -> Self:
        """Create fresh metadata for a new run.

        Args:
            run_id: Unique identifier for this run.
            runbook_path: Path to the runbook file.

        Returns:
            New RunMetadata with status='running'.

        """
        return cls(
            run_id=run_id,
            runbook_path=str(runbook_path),
            started_at=datetime.now(UTC),
            status="running",
        )

    # -------------------------------------------------------------------------
    # Status Transitions
    # -------------------------------------------------------------------------

    def mark_completed(self) -> None:
        """Transition status to 'completed' and set completed_at timestamp."""
        self.status = "completed"
        self.completed_at = datetime.now(UTC)

    def mark_failed(self) -> None:
        """Transition status to 'failed' and set completed_at timestamp."""
        self.status = "failed"
        self.completed_at = datetime.now(UTC)

    def mark_interrupted(self) -> None:
        """Transition status to 'interrupted' and set completed_at timestamp."""
        self.status = "interrupted"
        self.completed_at = datetime.now(UTC)

    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------

    @classmethod
    async def load(cls, store: ArtifactStore, run_id: str) -> Self:
        """Load metadata from store.

        Args:
            store: The artifact store to load from.
            run_id: The run identifier.

        Returns:
            Loaded RunMetadata.

        Raises:
            ArtifactNotFoundError: If metadata does not exist for this run.

        """
        data = await store.load_system_data(run_id, "metadata")
        return cls.model_validate(data)

    async def save(self, store: ArtifactStore) -> None:
        """Persist metadata to store.

        Args:
            store: The artifact store to save to.

        """
        data = self.model_dump(mode="json")
        await store.save_system_data(self.run_id, "metadata", data)
