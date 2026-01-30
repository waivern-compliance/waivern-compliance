"""Tests for ArtifactStore.list_runs() method."""

from pathlib import Path

from waivern_artifact_store.filesystem import LocalFilesystemStore
from waivern_artifact_store.in_memory import AsyncInMemoryStore

# =============================================================================
# Filesystem Store Tests
# =============================================================================


class TestLocalFilesystemStoreListRuns:
    """Tests for LocalFilesystemStore.list_runs()."""

    async def test_list_runs_returns_all_run_ids(self, tmp_path: Path) -> None:
        """Returns all run IDs that have been created."""
        # Arrange
        store = LocalFilesystemStore(tmp_path)

        # Create runs by saving data
        await store.save_json("run-001", "_system/state", {"status": "completed"})
        await store.save_json("run-002", "_system/state", {"status": "failed"})
        await store.save_json("run-003", "_system/state", {"status": "running"})

        # Act
        run_ids = await store.list_runs()

        # Assert
        assert run_ids == ["run-001", "run-002", "run-003"]

    async def test_list_runs_returns_empty_for_no_runs(self, tmp_path: Path) -> None:
        """Returns empty list when no runs exist."""
        # Arrange
        store = LocalFilesystemStore(tmp_path)

        # Act
        run_ids = await store.list_runs()

        # Assert
        assert run_ids == []


# =============================================================================
# In-Memory Store Tests
# =============================================================================


class TestAsyncInMemoryStoreListRuns:
    """Tests for AsyncInMemoryStore.list_runs()."""

    async def test_list_runs_returns_all_run_ids(self) -> None:
        """Returns all run IDs that have been created."""
        # Arrange
        store = AsyncInMemoryStore()

        # Create runs by saving data (some with messages, some with JSON only)
        await store.save_json("run-001", "_system/state", {"status": "completed"})
        await store.save_json("run-002", "_system/state", {"status": "failed"})
        await store.save_json("run-003", "_system/state", {"status": "running"})

        # Act
        run_ids = await store.list_runs()

        # Assert
        assert run_ids == ["run-001", "run-002", "run-003"]

    async def test_list_runs_returns_empty_for_no_runs(self) -> None:
        """Returns empty list when no runs exist."""
        # Arrange
        store = AsyncInMemoryStore()

        # Act
        run_ids = await store.list_runs()

        # Assert
        assert run_ids == []
