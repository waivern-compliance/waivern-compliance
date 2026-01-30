"""Tests for RunMetadata model and runbook hash computation."""

from pathlib import Path

import pytest
from waivern_artifact_store.errors import ArtifactNotFoundError
from waivern_artifact_store.in_memory import AsyncInMemoryStore

from waivern_orchestration.run_metadata import RunMetadata, compute_runbook_hash

# =============================================================================
# RunMetadata Model Tests
# =============================================================================


class TestRunMetadataFresh:
    """Tests for creating fresh RunMetadata."""

    def test_fresh_creates_metadata_with_running_status(self) -> None:
        """Fresh RunMetadata has status='running' and required fields populated."""
        # Arrange
        run_id = "test-run-123"
        runbook_path = Path("/path/to/runbook.yaml")
        runbook_hash = "sha256:abc123"

        # Act
        metadata = RunMetadata.fresh(
            run_id=run_id,
            runbook_path=runbook_path,
            runbook_hash=runbook_hash,
        )

        # Assert
        assert metadata.run_id == run_id
        assert metadata.runbook_path == str(runbook_path)
        assert metadata.runbook_hash == runbook_hash
        assert metadata.status == "running"
        assert metadata.started_at is not None
        assert metadata.completed_at is None


class TestRunMetadataPersistence:
    """Tests for RunMetadata save/load operations."""

    async def test_save_then_load_round_trip_preserves_metadata(self) -> None:
        """Saved metadata can be loaded with all fields intact."""
        # Arrange
        store = AsyncInMemoryStore()
        run_id = "test-run-456"

        original = RunMetadata.fresh(
            run_id=run_id,
            runbook_path=Path("/path/to/runbook.yaml"),
            runbook_hash="sha256:abc123def456",
        )

        # Act
        await original.save(store)
        loaded = await RunMetadata.load(store, run_id)

        # Assert
        assert loaded.run_id == original.run_id
        assert loaded.runbook_path == original.runbook_path
        assert loaded.runbook_hash == original.runbook_hash
        assert loaded.status == original.status
        assert loaded.started_at == original.started_at
        assert loaded.completed_at == original.completed_at

    async def test_load_raises_error_for_missing_run(self) -> None:
        """Loading non-existent run raises ArtifactNotFoundError."""
        # Arrange
        store = AsyncInMemoryStore()

        # Act & Assert
        with pytest.raises(ArtifactNotFoundError):
            await RunMetadata.load(store, "nonexistent-run")


class TestRunMetadataStatusTransitions:
    """Tests for RunMetadata status transitions."""

    def test_mark_completed_sets_status_and_timestamp(self) -> None:
        """mark_completed() transitions status and sets completed_at."""
        # Arrange
        metadata = RunMetadata.fresh(
            run_id="test-run",
            runbook_path=Path("/path/to/runbook.yaml"),
            runbook_hash="sha256:abc123",
        )
        assert metadata.status == "running"
        assert metadata.completed_at is None

        # Act
        metadata.mark_completed()

        # Assert
        assert metadata.status == "completed"
        assert metadata.completed_at is not None

    def test_mark_failed_sets_status_and_timestamp(self) -> None:
        """mark_failed() transitions status and sets completed_at."""
        # Arrange
        metadata = RunMetadata.fresh(
            run_id="test-run",
            runbook_path=Path("/path/to/runbook.yaml"),
            runbook_hash="sha256:abc123",
        )
        assert metadata.status == "running"
        assert metadata.completed_at is None

        # Act
        metadata.mark_failed()

        # Assert
        assert metadata.status == "failed"
        assert metadata.completed_at is not None


# =============================================================================
# Runbook Hash Computation Tests
# =============================================================================


class TestRunbookHash:
    """Tests for runbook hash computation."""

    def test_compute_runbook_hash_returns_sha256(self, tmp_path: Path) -> None:
        """Hash is computed as SHA-256 with correct format."""
        # Arrange
        runbook_file = tmp_path / "runbook.yaml"
        runbook_file.write_text("name: test\ndescription: test runbook\n")

        # Act
        hash_value = compute_runbook_hash(runbook_file)

        # Assert - should be sha256:<64 hex chars>
        assert hash_value.startswith("sha256:")
        hex_part = hash_value.split(":")[1]
        assert len(hex_part) == 64  # SHA-256 produces 64 hex characters
        assert all(c in "0123456789abcdef" for c in hex_part)

    def test_compute_runbook_hash_is_deterministic(self, tmp_path: Path) -> None:
        """Same file content always produces same hash."""
        # Arrange
        runbook_file = tmp_path / "runbook.yaml"
        runbook_file.write_text("name: test\ndescription: test runbook\n")

        # Act
        hash1 = compute_runbook_hash(runbook_file)
        hash2 = compute_runbook_hash(runbook_file)

        # Assert
        assert hash1 == hash2

    def test_compute_runbook_hash_changes_when_file_modified(
        self, tmp_path: Path
    ) -> None:
        """Different file content produces different hash."""
        # Arrange
        runbook_file = tmp_path / "runbook.yaml"
        runbook_file.write_text("name: test\ndescription: original\n")
        original_hash = compute_runbook_hash(runbook_file)

        # Act - modify the file
        runbook_file.write_text("name: test\ndescription: modified\n")
        modified_hash = compute_runbook_hash(runbook_file)

        # Assert
        assert original_hash != modified_hash
