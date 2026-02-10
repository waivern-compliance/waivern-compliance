"""Tests for BatchJob model persistence."""

from datetime import UTC, datetime

import pytest
from waivern_artifact_store.errors import ArtifactNotFoundError
from waivern_artifact_store.in_memory import AsyncInMemoryStore

from waivern_llm.batch_job import BatchJob


class TestBatchJobSaveAndLoad:
    """Tests for save() and load() persistence round-trips."""

    async def test_save_then_load_round_trip_preserves_all_fields(self) -> None:
        store = AsyncInMemoryStore()
        submitted_at = datetime(2025, 6, 15, 10, 30, 0, tzinfo=UTC)
        completed_at = datetime(2025, 6, 15, 11, 0, 0, tzinfo=UTC)
        job = BatchJob(
            batch_id="batch-abc123",
            run_id="run-456",
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            status="completed",
            cache_keys=["key-a", "key-b", "key-c"],
            request_count=3,
            submitted_at=submitted_at,
            completed_at=completed_at,
        )

        await job.save(store)
        loaded = await BatchJob.load(store, "run-456", "batch-abc123")

        assert loaded.batch_id == "batch-abc123"
        assert loaded.run_id == "run-456"
        assert loaded.provider == "anthropic"
        assert loaded.model == "claude-sonnet-4-5-20250929"
        assert loaded.status == "completed"
        assert loaded.cache_keys == ["key-a", "key-b", "key-c"]
        assert loaded.request_count == 3
        assert loaded.submitted_at == submitted_at
        assert loaded.completed_at == completed_at

    async def test_save_overwrites_existing_on_same_batch_id(self) -> None:
        store = AsyncInMemoryStore()
        job = BatchJob(
            batch_id="batch-1",
            run_id="run-1",
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            status="submitted",
            cache_keys=["key-a"],
            request_count=1,
            submitted_at=datetime(2025, 6, 15, 10, 0, 0, tzinfo=UTC),
            completed_at=None,
        )
        await job.save(store)

        # Update status and save again
        job.status = "completed"
        job.completed_at = datetime(2025, 6, 15, 11, 0, 0, tzinfo=UTC)
        await job.save(store)

        loaded = await BatchJob.load(store, "run-1", "batch-1")
        assert loaded.status == "completed"
        assert loaded.completed_at is not None

    async def test_load_raises_not_found_for_missing_batch_job(self) -> None:
        store = AsyncInMemoryStore()

        with pytest.raises(ArtifactNotFoundError):
            await BatchJob.load(store, "run-1", "nonexistent")


class TestBatchJobListForRun:
    """Tests for list_for_run() enumeration."""

    async def test_list_for_run_returns_all_saved_jobs(self) -> None:
        store = AsyncInMemoryStore()
        for i, batch_id in enumerate(["batch-a", "batch-b"]):
            job = BatchJob(
                batch_id=batch_id,
                run_id="run-1",
                provider="anthropic",
                model="claude-sonnet-4-5-20250929",
                status="submitted",
                cache_keys=[f"key-{i}"],
                request_count=1,
                submitted_at=datetime(2025, 6, 15, 10, 0, 0, tzinfo=UTC),
                completed_at=None,
            )
            await job.save(store)

        jobs = await BatchJob.list_for_run(store, "run-1")

        assert len(jobs) == 2
        batch_ids = {j.batch_id for j in jobs}
        assert batch_ids == {"batch-a", "batch-b"}

    async def test_list_for_run_returns_empty_for_no_jobs(self) -> None:
        store = AsyncInMemoryStore()

        jobs = await BatchJob.list_for_run(store, "run-1")

        assert jobs == []
