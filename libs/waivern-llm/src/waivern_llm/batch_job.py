"""BatchJob model for tracking batch submissions within a run.

A run can have multiple BatchJob records — one per artifact that calls
``llm.complete()`` in batch mode.  Each BatchJob tracks the provider's
batch identifier, the cache keys that need updating on completion, and
the current processing status.

Follows the ``ExecutionState``/``RunMetadata`` persistence pattern with
``save()``, ``load()``, and ``list_for_run()`` class methods.
"""

from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import BaseModel
from waivern_artifact_store.base import ArtifactStore

from waivern_llm.batch_types import BatchStatusLiteral


class BatchJob(BaseModel):
    """Tracks a single batch submission within a run.

    Fields ``provider`` and ``model`` are metadata — they record what was
    used at submission time.  The poller validates that the resolved
    provider matches these fields before polling.
    """

    batch_id: str
    """Provider's batch identifier."""

    run_id: str
    """Which run owns this batch."""

    provider: str
    """Provider name at submission (validation/audit)."""

    model: str
    """Model name at submission (validation/audit)."""

    status: BatchStatusLiteral
    """Current batch processing status."""

    cache_keys: list[str]
    """Cache entries to update on completion."""

    request_count: int
    """Number of prompts submitted."""

    submitted_at: datetime
    """Submission timestamp (UTC)."""

    completed_at: datetime | None
    """Completion timestamp (UTC). None if still processing."""

    async def save(self, store: ArtifactStore) -> None:
        """Persist batch job to store.

        Uses upsert semantics — overwrites if batch_id already exists.

        Args:
            store: The artifact store to save to.

        """
        data = self.model_dump(mode="json")
        await store.save_batch_job(self.run_id, self.batch_id, data)

    @classmethod
    async def load(cls, store: ArtifactStore, run_id: str, batch_id: str) -> Self:
        """Load a batch job from store.

        Args:
            store: The artifact store to load from.
            run_id: The run identifier.
            batch_id: The provider's batch identifier.

        Returns:
            Loaded BatchJob.

        Raises:
            ArtifactNotFoundError: If batch job does not exist.

        """
        data = await store.load_batch_job(run_id, batch_id)
        return cls.model_validate(data)

    @classmethod
    async def list_for_run(cls, store: ArtifactStore, run_id: str) -> list[Self]:
        """Load all batch jobs for a run.

        Args:
            store: The artifact store to load from.
            run_id: The run identifier.

        Returns:
            List of BatchJob instances. Empty list if no batch jobs exist.

        """
        batch_ids = await store.list_batch_jobs(run_id)
        return [await cls.load(store, run_id, bid) for bid in batch_ids]
