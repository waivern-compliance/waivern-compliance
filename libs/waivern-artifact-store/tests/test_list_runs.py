"""Tests for ArtifactStore.list_runs() method."""

from pathlib import Path
from typing import Any

import pytest

from waivern_artifact_store.base import ArtifactStore
from waivern_artifact_store.filesystem import LocalFilesystemStore
from waivern_artifact_store.in_memory import AsyncInMemoryStore


@pytest.fixture
def filesystem_store(tmp_path: Path) -> ArtifactStore:
    """Create a filesystem store for testing."""
    return LocalFilesystemStore(tmp_path)


@pytest.fixture
def in_memory_store() -> ArtifactStore:
    """Create an in-memory store for testing."""
    return AsyncInMemoryStore()


class TestArtifactStoreListRuns:
    """Tests for ArtifactStore.list_runs() - parametrised across implementations."""

    @pytest.fixture(params=["filesystem", "in_memory"])
    def store(
        self,
        request: pytest.FixtureRequest,
        filesystem_store: ArtifactStore,
        in_memory_store: ArtifactStore,
    ) -> ArtifactStore:
        """Parametrised fixture providing both store implementations."""
        stores: dict[str, Any] = {
            "filesystem": filesystem_store,
            "in_memory": in_memory_store,
        }
        return stores[request.param]

    async def test_list_runs_returns_all_run_ids(self, store: ArtifactStore) -> None:
        """Returns all run IDs that have been created."""
        # Arrange - Create runs by saving data
        await store.save_json("run-001", "_system/state", {"status": "completed"})
        await store.save_json("run-002", "_system/state", {"status": "failed"})
        await store.save_json("run-003", "_system/state", {"status": "running"})

        # Act
        run_ids = await store.list_runs()

        # Assert
        assert run_ids == ["run-001", "run-002", "run-003"]

    async def test_list_runs_returns_empty_for_no_runs(
        self, store: ArtifactStore
    ) -> None:
        """Returns empty list when no runs exist."""
        # Act
        run_ids = await store.list_runs()

        # Assert
        assert run_ids == []
