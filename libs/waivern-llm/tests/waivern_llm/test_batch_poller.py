"""Tests for BatchResultPoller.

Business behaviour: Polls batch API providers for completed results,
updates cache entries from pending to completed (or failed), and
updates BatchJob status accordingly.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

from waivern_artifact_store.in_memory import AsyncInMemoryStore

from waivern_llm.batch_job import BatchJob
from waivern_llm.batch_poller import BatchResultPoller, PollResult
from waivern_llm.batch_types import BatchResult, BatchStatus, BatchStatusLiteral
from waivern_llm.cache import CacheEntry

# =============================================================================
# Helpers
# =============================================================================


def _create_batch_job(  # noqa: PLR0913 - test helper with many optional params
    batch_id: str = "batch-1",
    run_id: str = "run-1",
    provider: str = "anthropic",
    model: str = "claude-sonnet-4-5-20250929",
    status: BatchStatusLiteral = "submitted",
    cache_keys: list[str] | None = None,
    request_count: int = 2,
) -> BatchJob:
    """Create a BatchJob with sensible defaults for testing."""
    return BatchJob(
        batch_id=batch_id,
        run_id=run_id,
        provider=provider,
        model=model,
        status=status,
        cache_keys=cache_keys or ["key-a", "key-b"],
        request_count=request_count,
        submitted_at=datetime(2025, 6, 15, 10, 0, 0, tzinfo=UTC),
        completed_at=None,
    )


def _create_pending_cache_entry(
    batch_id: str = "batch-1",
    model_name: str = "claude-sonnet-4-5-20250929",
) -> CacheEntry:
    """Create a pending cache entry tied to a batch."""
    return CacheEntry(
        status="pending",
        response=None,
        batch_id=batch_id,
        model_name=model_name,
        response_model_name="MockResponse",
    )


# =============================================================================
# Tests
# =============================================================================


class TestBatchResultPoller:
    """Tests for BatchResultPoller.poll_run()."""

    async def test_completed_batch_updates_cache_entries_and_job(self) -> None:
        """Completed batch → cache entries updated to completed, job marked completed."""
        # Arrange — one submitted job with two pending cache entries
        store = AsyncInMemoryStore()
        job = _create_batch_job(cache_keys=["key-a", "key-b"])
        await job.save(store)

        for key in ["key-a", "key-b"]:
            entry = _create_pending_cache_entry()
            await store.cache_set("run-1", key, entry.model_dump())

        # Provider returns completed status and results for both keys
        provider = Mock()
        provider.get_batch_status = AsyncMock(
            return_value=BatchStatus(
                batch_id="batch-1",
                status="completed",
                completed_count=2,
                failed_count=0,
                total_count=2,
            )
        )
        provider.get_batch_results = AsyncMock(
            return_value=[
                BatchResult(
                    custom_id="key-a",
                    status="completed",
                    response={"valid": True, "reason": "ok"},
                    error=None,
                ),
                BatchResult(
                    custom_id="key-b",
                    status="completed",
                    response={"valid": False, "reason": "issue found"},
                    error=None,
                ),
            ]
        )

        poller = BatchResultPoller(
            store=store,
            provider=provider,
            provider_name="anthropic",
            model_name="claude-sonnet-4-5-20250929",
        )

        # Act
        result = await poller.poll_run("run-1")

        # Assert — PollResult counts
        assert isinstance(result, PollResult)
        assert result.completed == 1  # 1 batch completed
        assert result.failed == 0
        assert result.pending == 0
        assert result.errors == []

        # Assert — cache entries updated to completed with response data
        cached_a = await store.cache_get("run-1", "key-a")
        assert cached_a is not None
        entry_a = CacheEntry.model_validate(cached_a)
        assert entry_a.status == "completed"
        assert entry_a.response == {"valid": True, "reason": "ok"}

        cached_b = await store.cache_get("run-1", "key-b")
        assert cached_b is not None
        entry_b = CacheEntry.model_validate(cached_b)
        assert entry_b.status == "completed"
        assert entry_b.response == {"valid": False, "reason": "issue found"}

        # Assert — BatchJob updated to completed with timestamp
        updated_job = await BatchJob.load(store, "run-1", "batch-1")
        assert updated_job.status == "completed"
        assert updated_job.completed_at is not None

    async def test_in_progress_batch_updates_job_status(self) -> None:
        """In-progress batch → job status updated, cache entries unchanged."""
        # Arrange — submitted job with pending cache entries
        store = AsyncInMemoryStore()
        job = _create_batch_job(status="submitted", cache_keys=["key-a"])
        await job.save(store)

        entry = _create_pending_cache_entry()
        await store.cache_set("run-1", "key-a", entry.model_dump())

        # Provider returns in_progress status
        provider = Mock()
        provider.get_batch_status = AsyncMock(
            return_value=BatchStatus(
                batch_id="batch-1",
                status="in_progress",
                completed_count=0,
                failed_count=0,
                total_count=1,
            )
        )

        poller = BatchResultPoller(
            store=store,
            provider=provider,
            provider_name="anthropic",
            model_name="claude-sonnet-4-5-20250929",
        )

        # Act
        result = await poller.poll_run("run-1")

        # Assert — PollResult shows 1 pending, no completed/failed
        assert result.completed == 0
        assert result.failed == 0
        assert result.pending == 1
        assert result.errors == []

        # Assert — cache entry still pending (unchanged)
        cached = await store.cache_get("run-1", "key-a")
        assert cached is not None
        assert CacheEntry.model_validate(cached).status == "pending"

        # Assert — job status updated from submitted to in_progress
        updated_job = await BatchJob.load(store, "run-1", "batch-1")
        assert updated_job.status == "in_progress"
        assert updated_job.completed_at is None

        # Assert — get_batch_results NOT called (batch not complete)
        provider.get_batch_results = AsyncMock()
        provider.get_batch_results.assert_not_called()

    async def test_failed_batch_updates_cache_entries_and_job(self) -> None:
        """Failed batch → cache entries updated to failed, job marked failed."""
        # Arrange — submitted job with two pending cache entries
        store = AsyncInMemoryStore()
        job = _create_batch_job(cache_keys=["key-a", "key-b"])
        await job.save(store)

        for key in ["key-a", "key-b"]:
            entry = _create_pending_cache_entry()
            await store.cache_set("run-1", key, entry.model_dump())

        # Provider returns failed status
        provider = Mock()
        provider.get_batch_status = AsyncMock(
            return_value=BatchStatus(
                batch_id="batch-1",
                status="failed",
                completed_count=0,
                failed_count=2,
                total_count=2,
            )
        )

        poller = BatchResultPoller(
            store=store,
            provider=provider,
            provider_name="anthropic",
            model_name="claude-sonnet-4-5-20250929",
        )

        # Act
        result = await poller.poll_run("run-1")

        # Assert — PollResult counts
        assert result.completed == 0
        assert result.failed == 1  # 1 batch failed
        assert result.pending == 0
        assert result.errors == []

        # Assert — cache entries updated to failed with no response
        for key in ["key-a", "key-b"]:
            cached = await store.cache_get("run-1", key)
            assert cached is not None
            entry = CacheEntry.model_validate(cached)
            assert entry.status == "failed"
            assert entry.response is None

        # Assert — BatchJob updated to failed with timestamp
        updated_job = await BatchJob.load(store, "run-1", "batch-1")
        assert updated_job.status == "failed"
        assert updated_job.completed_at is not None

        # Assert — get_batch_results NOT called (batch failed entirely)
        assert (
            not hasattr(provider, "get_batch_results")
            or not provider.get_batch_results.called
        )

    async def test_provider_mismatch_adds_error_and_skips_job(self) -> None:
        """Provider/model mismatch → error added to PollResult, job skipped."""
        # Arrange — job recorded for "openai" provider, poller configured for "anthropic"
        store = AsyncInMemoryStore()
        job = _create_batch_job(provider="openai", model="gpt-4o")
        await job.save(store)

        provider = Mock()

        poller = BatchResultPoller(
            store=store,
            provider=provider,
            provider_name="anthropic",
            model_name="claude-sonnet-4-5-20250929",
        )

        # Act
        result = await poller.poll_run("run-1")

        # Assert — error reported, job not polled
        assert result.completed == 0
        assert result.failed == 0
        assert result.pending == 0
        assert len(result.errors) == 1
        assert "mismatch" in result.errors[0]
        assert "openai/gpt-4o" in result.errors[0]
        assert "anthropic/claude-sonnet-4-5-20250929" in result.errors[0]

        # Assert — provider never called (job was skipped)
        provider.get_batch_status.assert_not_called()

    async def test_already_completed_jobs_are_filtered_out(self) -> None:
        """Already completed/failed/cancelled jobs are not re-polled."""
        # Arrange — three jobs: completed, failed, cancelled
        store = AsyncInMemoryStore()

        terminal_states: list[tuple[BatchStatusLiteral, str]] = [
            ("completed", "batch-done"),
            ("failed", "batch-fail"),
            ("cancelled", "batch-cancel"),
        ]
        for status, batch_id in terminal_states:
            job = _create_batch_job(batch_id=batch_id, status=status)
            await job.save(store)

        provider = Mock()

        poller = BatchResultPoller(
            store=store,
            provider=provider,
            provider_name="anthropic",
            model_name="claude-sonnet-4-5-20250929",
        )

        # Act
        result = await poller.poll_run("run-1")

        # Assert — nothing polled, all zeroes
        assert result.completed == 0
        assert result.failed == 0
        assert result.pending == 0
        assert result.errors == []

        # Assert — provider never called
        provider.get_batch_status.assert_not_called()

    async def test_completed_batch_with_mixed_per_prompt_results(self) -> None:
        """Completed batch with some prompts failed → correct per-entry status."""
        # Arrange — one batch with two prompts: one succeeds, one fails
        store = AsyncInMemoryStore()
        job = _create_batch_job(cache_keys=["key-ok", "key-fail"])
        await job.save(store)

        for key in ["key-ok", "key-fail"]:
            entry = _create_pending_cache_entry()
            await store.cache_set("run-1", key, entry.model_dump())

        # Provider returns completed batch, but one prompt failed
        provider = Mock()
        provider.get_batch_status = AsyncMock(
            return_value=BatchStatus(
                batch_id="batch-1",
                status="completed",
                completed_count=1,
                failed_count=1,
                total_count=2,
            )
        )
        provider.get_batch_results = AsyncMock(
            return_value=[
                BatchResult(
                    custom_id="key-ok",
                    status="completed",
                    response={"valid": True, "reason": "looks good"},
                    error=None,
                ),
                BatchResult(
                    custom_id="key-fail",
                    status="failed",
                    response=None,
                    error="Content policy violation",
                ),
            ]
        )

        poller = BatchResultPoller(
            store=store,
            provider=provider,
            provider_name="anthropic",
            model_name="claude-sonnet-4-5-20250929",
        )

        # Act
        result = await poller.poll_run("run-1")

        # Assert — batch counts as completed (the batch itself completed)
        assert result.completed == 1
        assert result.failed == 0
        assert result.pending == 0

        # Assert — successful prompt has completed cache entry with response
        cached_ok = await store.cache_get("run-1", "key-ok")
        assert cached_ok is not None
        entry_ok = CacheEntry.model_validate(cached_ok)
        assert entry_ok.status == "completed"
        assert entry_ok.response == {"valid": True, "reason": "looks good"}

        # Assert — failed prompt has failed cache entry with no response
        cached_fail = await store.cache_get("run-1", "key-fail")
        assert cached_fail is not None
        entry_fail = CacheEntry.model_validate(cached_fail)
        assert entry_fail.status == "failed"
        assert entry_fail.response is None
