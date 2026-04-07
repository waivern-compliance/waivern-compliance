"""Tests for RunMetadata model."""

from pathlib import Path

import pytest
from waivern_artifact_store.errors import ArtifactNotFoundError
from waivern_artifact_store.in_memory import AsyncInMemoryStore

from waivern_orchestration.run_metadata import RunMetadata

# =============================================================================
# RunMetadata Model Tests
# =============================================================================


class TestRunMetadataFresh:
    """Tests for creating fresh RunMetadata."""

    def test_fresh_creates_metadata_with_running_status(self) -> None:
        """Fresh RunMetadata has status='running' and required fields populated."""
        run_id = "test-run-123"
        runbook_path = Path("/path/to/runbook.yaml")

        metadata = RunMetadata.fresh(
            run_id=run_id,
            runbook_path=runbook_path,
        )

        assert metadata.run_id == run_id
        assert metadata.runbook_path == str(runbook_path)
        assert metadata.status == "running"
        assert metadata.started_at is not None
        assert metadata.completed_at is None


class TestRunMetadataPersistence:
    """Tests for RunMetadata save/load operations."""

    async def test_save_then_load_round_trip_preserves_metadata(self) -> None:
        """Saved metadata can be loaded with all fields intact."""
        store = AsyncInMemoryStore()
        run_id = "test-run-456"

        original = RunMetadata.fresh(
            run_id=run_id,
            runbook_path=Path("/path/to/runbook.yaml"),
        )

        await original.save(store)
        loaded = await RunMetadata.load(store, run_id)

        assert loaded.run_id == original.run_id
        assert loaded.runbook_path == original.runbook_path
        assert loaded.status == original.status
        assert loaded.started_at == original.started_at
        assert loaded.completed_at == original.completed_at

    async def test_load_raises_error_for_missing_run(self) -> None:
        """Loading non-existent run raises ArtifactNotFoundError."""
        store = AsyncInMemoryStore()

        with pytest.raises(ArtifactNotFoundError):
            await RunMetadata.load(store, "nonexistent-run")


class TestRunMetadataStatusTransitions:
    """Tests for RunMetadata status transitions."""

    def test_mark_completed_sets_status_and_timestamp(self) -> None:
        """mark_completed() transitions status and sets completed_at."""
        metadata = RunMetadata.fresh(
            run_id="test-run",
            runbook_path=Path("/path/to/runbook.yaml"),
        )
        assert metadata.status == "running"
        assert metadata.completed_at is None

        metadata.mark_completed()

        assert metadata.status == "completed"
        assert metadata.completed_at is not None

    def test_mark_interrupted_sets_status_and_timestamp(self) -> None:
        """mark_interrupted() transitions status and sets completed_at."""
        metadata = RunMetadata.fresh(
            run_id="test-run",
            runbook_path=Path("/path/to/runbook.yaml"),
        )
        assert metadata.status == "running"
        assert metadata.completed_at is None

        metadata.mark_interrupted()

        assert metadata.status == "interrupted"
        assert metadata.completed_at is not None

    def test_mark_failed_sets_status_and_timestamp(self) -> None:
        """mark_failed() transitions status and sets completed_at."""
        metadata = RunMetadata.fresh(
            run_id="test-run",
            runbook_path=Path("/path/to/runbook.yaml"),
        )
        assert metadata.status == "running"
        assert metadata.completed_at is None

        metadata.mark_failed()

        assert metadata.status == "failed"
        assert metadata.completed_at is not None
