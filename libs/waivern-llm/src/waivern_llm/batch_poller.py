"""Batch result poller for checking and collecting batch API results.

Polls a batch-capable LLM provider for completed results and updates
the cache entries from ``pending`` to ``completed`` (or ``failed``).
This bridges the gap between ``DefaultLLMService._complete_batch()``
(which submits work and raises ``PendingBatchError``) and the resume
path (which expects all cache entries to be completed).

Typical usage from the CLI::

    poller = BatchResultPoller(store, provider, "anthropic", "claude-sonnet-4-5")
    result = await poller.poll_run(run_id)
    if result.pending == 0:
        print("All batches complete — ready to resume")
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from pydantic import BaseModel

from waivern_llm.batch_job import BatchJob
from waivern_llm.cache import CacheEntry
from waivern_llm.providers.protocol import BatchLLMProvider

if TYPE_CHECKING:
    from waivern_artifact_store.base import ArtifactStore
    from waivern_artifact_store.llm_cache import LLMCache


class PollResult(BaseModel):
    """Summary of a poll_run() invocation."""

    completed: int = 0
    """Number of batches that completed in this poll."""

    failed: int = 0
    """Number of batches that failed in this poll."""

    pending: int = 0
    """Number of batches still in progress."""

    errors: list[str] = []
    """Non-fatal errors encountered (e.g. provider mismatch)."""


class BatchResultPoller:
    """Polls batch API providers and updates cache entries."""

    def __init__(
        self,
        store: ArtifactStore,
        provider: BatchLLMProvider,
        provider_name: str,
        model_name: str,
    ) -> None:
        """Initialise the poller.

        Args:
            store: Artifact store for cache and batch job persistence.
            provider: Batch-capable LLM provider for status/results queries.
            provider_name: Expected provider name (validated against BatchJob).
            model_name: Expected model name (validated against BatchJob).

        """
        self._store = store
        self._cache: LLMCache = cast("LLMCache", store)
        self._provider = provider
        self._provider_name = provider_name
        self._model_name = model_name

    async def poll_run(self, run_id: str) -> PollResult:
        """Poll all pending batch jobs for a run.

        Orchestrates the polling flow:
        1. Load all BatchJobs for the run
        2. Filter to active jobs (submitted/in_progress)
        3. For each job, validate provider/model match
        4. Query provider for batch status
        5. If completed → fetch results, update cache entries, update job
        6. If still in progress → update job status if changed
        7. If failed → update cache entries to failed, update job

        Args:
            run_id: The run identifier to poll jobs for.

        Returns:
            PollResult with counts and any errors encountered.

        """
        jobs = await BatchJob.list_for_run(self._store, run_id)
        active_jobs = [j for j in jobs if j.status in ("submitted", "in_progress")]

        result = PollResult()

        for job in active_jobs:
            if job.provider != self._provider_name or job.model != self._model_name:
                result.errors.append(
                    f"Batch {job.batch_id}: provider/model mismatch — "
                    f"job has {job.provider}/{job.model}, "
                    f"poller has {self._provider_name}/{self._model_name}"
                )
                continue

            status = await self._provider.get_batch_status(job.batch_id)

            if status.status == "completed":
                await self._handle_completed(run_id, job, result)
            elif status.status == "failed":
                await self._handle_failed(run_id, job, result)
            else:
                # Still in progress — update job status if changed
                if job.status != status.status:
                    job.status = status.status
                    await job.save(self._store)
                result.pending += 1

        return result

    async def _handle_completed(
        self,
        run_id: str,
        job: BatchJob,
        result: PollResult,
    ) -> None:
        """Process a completed batch — fetch results and update cache entries."""
        batch_results = await self._provider.get_batch_results(job.batch_id)

        results_by_id = {r.custom_id: r for r in batch_results}

        for cache_key in job.cache_keys:
            batch_result = results_by_id.get(cache_key)
            if batch_result is None:
                continue

            cached_data = await self._cache.cache_get(run_id, cache_key)
            if cached_data is None:
                continue

            entry = CacheEntry.model_validate(cached_data)
            if batch_result.status == "completed":
                entry.status = "completed"
                entry.response = batch_result.response
            else:
                entry.status = "failed"
                entry.response = None

            await self._cache.cache_set(run_id, cache_key, entry.model_dump())

        job.status = "completed"
        job.completed_at = datetime.now(UTC)
        await job.save(self._store)
        result.completed += 1

    async def _handle_failed(
        self,
        run_id: str,
        job: BatchJob,
        result: PollResult,
    ) -> None:
        """Process a failed batch — mark all cache entries as failed."""
        for cache_key in job.cache_keys:
            cached_data = await self._cache.cache_get(run_id, cache_key)
            if cached_data is None:
                continue

            entry = CacheEntry.model_validate(cached_data)
            entry.status = "failed"
            entry.response = None
            await self._cache.cache_set(run_id, cache_key, entry.model_dump())

        job.status = "failed"
        job.completed_at = datetime.now(UTC)
        await job.save(self._store)
        result.failed += 1
