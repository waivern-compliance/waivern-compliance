"""Tests for AsyncInMemoryStore implementation."""

import pytest
from waivern_core import JsonValue
from waivern_core.message import Message
from waivern_core.schemas import Schema

from waivern_artifact_store.errors import ArtifactNotFoundError
from waivern_artifact_store.in_memory import AsyncInMemoryStore

# =============================================================================
# Save Artifact Tests
# =============================================================================


class TestAsyncInMemoryStoreSaveArtifact:
    """Tests for the save_artifact() method."""

    async def test_save_artifact_stores_message_retrievable_by_get(self) -> None:
        store = AsyncInMemoryStore()
        message = Message(
            id="msg-1",
            content={"data": "test-value"},
            schema=Schema("test_schema", "1.0.0"),
        )

        await store.save_artifact("test-run", "my_artifact", message)

        retrieved = await store.get_artifact("test-run", "my_artifact")
        assert retrieved.id == "msg-1"
        assert retrieved.content == {"data": "test-value"}

    async def test_save_artifact_overwrites_existing(self) -> None:
        store = AsyncInMemoryStore()
        original = Message(
            id="msg-1",
            content={"version": "original"},
            schema=Schema("test_schema", "1.0.0"),
        )
        updated = Message(
            id="msg-2",
            content={"version": "updated"},
            schema=Schema("test_schema", "1.0.0"),
        )

        await store.save_artifact("test-run", "artifact", original)
        await store.save_artifact("test-run", "artifact", updated)

        retrieved = await store.get_artifact("test-run", "artifact")
        assert retrieved.id == "msg-2"
        assert retrieved.content == {"version": "updated"}


# =============================================================================
# Get Artifact Tests
# =============================================================================


class TestAsyncInMemoryStoreGetArtifact:
    """Tests for the get_artifact() method."""

    async def test_get_artifact_raises_not_found_for_missing(self) -> None:
        store = AsyncInMemoryStore()

        with pytest.raises(ArtifactNotFoundError):
            await store.get_artifact("test-run", "nonexistent")


# =============================================================================
# Artifact Exists Tests
# =============================================================================


class TestAsyncInMemoryStoreArtifactExists:
    """Tests for the artifact_exists() method."""

    async def test_artifact_exists_returns_true_after_save(self) -> None:
        store = AsyncInMemoryStore()
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save_artifact("test-run", "artifact", message)

        result = await store.artifact_exists("test-run", "artifact")

        assert result is True

    async def test_artifact_exists_returns_false_for_unsaved(self) -> None:
        store = AsyncInMemoryStore()

        result = await store.artifact_exists("test-run", "nonexistent")

        assert result is False


# =============================================================================
# Delete Artifact Tests
# =============================================================================


class TestAsyncInMemoryStoreDeleteArtifact:
    """Tests for the delete_artifact() method."""

    async def test_delete_artifact_removes_saved(self) -> None:
        store = AsyncInMemoryStore()
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save_artifact("test-run", "artifact", message)
        assert await store.artifact_exists("test-run", "artifact")

        await store.delete_artifact("test-run", "artifact")

        assert not await store.artifact_exists("test-run", "artifact")

    async def test_delete_artifact_does_not_raise_for_missing(self) -> None:
        store = AsyncInMemoryStore()

        # Should not raise any exception
        await store.delete_artifact("test-run", "nonexistent")


# =============================================================================
# List Artifacts Tests
# =============================================================================


class TestAsyncInMemoryStoreListArtifacts:
    """Tests for the list_artifacts() method."""

    async def test_list_artifacts_returns_all_saved_ids(self) -> None:
        store = AsyncInMemoryStore()
        for artifact_id in ["alpha", "beta", "gamma"]:
            message = Message(
                id=f"msg-{artifact_id}",
                content={"key": artifact_id},
                schema=Schema("test_schema", "1.0.0"),
            )
            await store.save_artifact("test-run", artifact_id, message)

        artifact_ids = await store.list_artifacts("test-run")

        assert set(artifact_ids) == {"alpha", "beta", "gamma"}

    async def test_list_artifacts_excludes_system_files(self) -> None:
        store = AsyncInMemoryStore()
        # Save a regular artifact (will implement system metadata separately)
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save_artifact("test-run", "findings", message)

        artifact_ids = await store.list_artifacts("test-run")

        assert "findings" in artifact_ids

    async def test_list_artifacts_returns_empty_for_no_artifacts(self) -> None:
        store = AsyncInMemoryStore()

        artifact_ids = await store.list_artifacts("test-run")

        assert artifact_ids == []


# =============================================================================
# Clear Artifacts Tests
# =============================================================================


class TestAsyncInMemoryStoreClearArtifacts:
    """Tests for the clear_artifacts() method."""

    async def test_clear_artifacts_removes_all(self) -> None:
        store = AsyncInMemoryStore()
        for artifact_id in ["alpha", "beta", "nested/gamma"]:
            message = Message(
                id=f"msg-{artifact_id}",
                content={"key": artifact_id},
                schema=Schema("test_schema", "1.0.0"),
            )
            await store.save_artifact("test-run", artifact_id, message)
        assert len(await store.list_artifacts("test-run")) == 3

        await store.clear_artifacts("test-run")

        assert await store.list_artifacts("test-run") == []


# =============================================================================
# Run Isolation Tests
# =============================================================================


class TestAsyncInMemoryStoreRunIsolation:
    """Tests for run isolation in singleton store."""

    async def test_different_runs_have_isolated_storage(self) -> None:
        store = AsyncInMemoryStore()
        message_run1 = Message(
            id="msg-run1",
            content={"run": "1"},
            schema=Schema("test_schema", "1.0.0"),
        )
        message_run2 = Message(
            id="msg-run2",
            content={"run": "2"},
            schema=Schema("test_schema", "1.0.0"),
        )

        await store.save_artifact("run-1", "artifact", message_run1)
        await store.save_artifact("run-2", "artifact", message_run2)

        retrieved_run1 = await store.get_artifact("run-1", "artifact")
        retrieved_run2 = await store.get_artifact("run-2", "artifact")

        assert retrieved_run1.content == {"run": "1"}
        assert retrieved_run2.content == {"run": "2"}

    async def test_clear_artifacts_only_affects_specified_run(self) -> None:
        store = AsyncInMemoryStore()
        for run_id in ["run-1", "run-2"]:
            message = Message(
                id=f"msg-{run_id}",
                content={"run": run_id},
                schema=Schema("test_schema", "1.0.0"),
            )
            await store.save_artifact(run_id, "artifact", message)

        await store.clear_artifacts("run-1")

        assert not await store.artifact_exists("run-1", "artifact")
        assert await store.artifact_exists("run-2", "artifact")


# =============================================================================
# List Runs Tests
# =============================================================================


class TestAsyncInMemoryStoreListRuns:
    """Tests for the list_runs() method."""

    async def test_list_runs_returns_all_run_ids(self) -> None:
        store = AsyncInMemoryStore()
        # Create runs by saving artifacts
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save_artifact("run-001", "artifact", message)
        await store.save_artifact("run-002", "artifact", message)
        await store.save_artifact("run-003", "artifact", message)

        run_ids = await store.list_runs()

        assert run_ids == ["run-001", "run-002", "run-003"]

    async def test_list_runs_returns_empty_for_no_runs(self) -> None:
        store = AsyncInMemoryStore()

        run_ids = await store.list_runs()

        assert run_ids == []


# =============================================================================
# Execution State Tests
# =============================================================================


class TestAsyncInMemoryStoreSaveExecutionState:
    """Tests for the save_execution_state() method."""

    async def test_save_execution_state_stores_data_retrievable_by_load(self) -> None:
        store = AsyncInMemoryStore()
        state_data: dict[str, JsonValue] = {
            "run_id": "test-run",
            "completed": ["artifact_a"],
            "failed": [],
            "skipped": [],
            "not_started": ["artifact_b"],
        }

        await store.save_execution_state("test-run", state_data)

        loaded = await store.load_execution_state("test-run")
        assert loaded["run_id"] == "test-run"
        assert loaded["completed"] == ["artifact_a"]

    async def test_save_execution_state_overwrites_existing(self) -> None:
        store = AsyncInMemoryStore()
        original_state: dict[str, JsonValue] = {"completed": [], "status": "running"}
        updated_state: dict[str, JsonValue] = {
            "completed": ["a", "b"],
            "status": "completed",
        }

        await store.save_execution_state("test-run", original_state)
        await store.save_execution_state("test-run", updated_state)

        loaded = await store.load_execution_state("test-run")
        assert loaded["status"] == "completed"
        assert loaded["completed"] == ["a", "b"]


class TestAsyncInMemoryStoreLoadExecutionState:
    """Tests for the load_execution_state() method."""

    async def test_load_execution_state_returns_saved_data(self) -> None:
        store = AsyncInMemoryStore()
        state_data: dict[str, JsonValue] = {
            "run_id": "test-run",
            "completed": ["a", "b"],
            "failed": ["c"],
            "skipped": ["d"],
            "not_started": [],
            "last_checkpoint": "2024-01-15T10:30:00Z",
        }
        await store.save_execution_state("test-run", state_data)

        loaded = await store.load_execution_state("test-run")

        assert loaded["run_id"] == "test-run"
        assert loaded["completed"] == ["a", "b"]
        assert loaded["failed"] == ["c"]
        assert loaded["skipped"] == ["d"]
        assert loaded["last_checkpoint"] == "2024-01-15T10:30:00Z"

    async def test_load_execution_state_raises_not_found_for_missing(self) -> None:
        store = AsyncInMemoryStore()

        with pytest.raises(ArtifactNotFoundError) as exc_info:
            await store.load_execution_state("nonexistent-run")

        assert "Execution state not found" in str(exc_info.value)


# =============================================================================
# Run Metadata Tests
# =============================================================================


class TestAsyncInMemoryStoreSaveRunMetadata:
    """Tests for the save_run_metadata() method."""

    async def test_save_run_metadata_stores_data_retrievable_by_load(self) -> None:
        store = AsyncInMemoryStore()
        metadata: dict[str, JsonValue] = {
            "run_id": "test-run",
            "runbook_path": "/path/to/runbook.yaml",
            "runbook_hash": "sha256:abc123",
            "status": "running",
            "started_at": "2024-01-15T10:00:00Z",
        }

        await store.save_run_metadata("test-run", metadata)

        loaded = await store.load_run_metadata("test-run")
        assert loaded["run_id"] == "test-run"
        assert loaded["status"] == "running"

    async def test_save_run_metadata_overwrites_existing(self) -> None:
        store = AsyncInMemoryStore()
        original: dict[str, JsonValue] = {"status": "running", "completed_at": None}
        updated: dict[str, JsonValue] = {
            "status": "completed",
            "completed_at": "2024-01-15T11:00:00Z",
        }

        await store.save_run_metadata("test-run", original)
        await store.save_run_metadata("test-run", updated)

        loaded = await store.load_run_metadata("test-run")
        assert loaded["status"] == "completed"
        assert loaded["completed_at"] == "2024-01-15T11:00:00Z"


class TestAsyncInMemoryStoreLoadRunMetadata:
    """Tests for the load_run_metadata() method."""

    async def test_load_run_metadata_returns_saved_data(self) -> None:
        store = AsyncInMemoryStore()
        metadata: dict[str, JsonValue] = {
            "run_id": "test-run",
            "runbook_path": "/path/to/runbook.yaml",
            "runbook_hash": "sha256:abc123def456",
            "status": "completed",
            "started_at": "2024-01-15T10:00:00Z",
            "completed_at": "2024-01-15T10:30:00Z",
        }
        await store.save_run_metadata("test-run", metadata)

        loaded = await store.load_run_metadata("test-run")

        assert loaded["run_id"] == "test-run"
        assert loaded["runbook_hash"] == "sha256:abc123def456"
        assert loaded["status"] == "completed"

    async def test_load_run_metadata_raises_not_found_for_missing(self) -> None:
        store = AsyncInMemoryStore()

        with pytest.raises(ArtifactNotFoundError) as exc_info:
            await store.load_run_metadata("nonexistent-run")

        assert "Run metadata not found" in str(exc_info.value)


# =============================================================================
# System Metadata Isolation Tests
# =============================================================================


class TestAsyncInMemoryStoreSystemMetadataIsolation:
    """Tests for isolation between artifacts and system metadata."""

    async def test_system_metadata_isolated_from_artifacts(self) -> None:
        """System metadata should not appear in artifact listings."""
        store = AsyncInMemoryStore()

        # Save both artifacts and system metadata
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save_artifact("test-run", "findings", message)
        state_data: dict[str, JsonValue] = {"completed": []}
        metadata: dict[str, JsonValue] = {"status": "running"}
        await store.save_execution_state("test-run", state_data)
        await store.save_run_metadata("test-run", metadata)

        # List artifacts should only show artifacts
        artifact_ids = await store.list_artifacts("test-run")

        assert artifact_ids == ["findings"]

    async def test_clear_artifacts_preserves_system_metadata(self) -> None:
        """clear_artifacts() should preserve system metadata."""
        store = AsyncInMemoryStore()

        # Save artifacts and system metadata
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save_artifact("test-run", "findings", message)
        state_data: dict[str, JsonValue] = {"completed": ["findings"]}
        metadata: dict[str, JsonValue] = {"status": "completed"}
        await store.save_execution_state("test-run", state_data)
        await store.save_run_metadata("test-run", metadata)

        # Clear artifacts
        await store.clear_artifacts("test-run")

        # Artifacts should be gone, system metadata should remain
        assert await store.list_artifacts("test-run") == []
        state = await store.load_execution_state("test-run")
        assert state["completed"] == ["findings"]
        metadata = await store.load_run_metadata("test-run")
        assert metadata["status"] == "completed"

    async def test_system_metadata_isolated_between_runs(self) -> None:
        """System metadata should be isolated between different runs."""
        store = AsyncInMemoryStore()

        # Save metadata for two different runs
        state_1: dict[str, JsonValue] = {"completed": ["a"]}
        state_2: dict[str, JsonValue] = {"completed": ["b", "c"]}
        await store.save_execution_state("run-1", state_1)
        await store.save_execution_state("run-2", state_2)

        # Load and verify isolation
        state_1 = await store.load_execution_state("run-1")
        state_2 = await store.load_execution_state("run-2")

        assert state_1["completed"] == ["a"]
        assert state_2["completed"] == ["b", "c"]

    async def test_list_runs_includes_runs_with_only_system_metadata(self) -> None:
        """list_runs() should include runs that only have system metadata."""
        store = AsyncInMemoryStore()

        # Run with only system metadata (no artifacts)
        state_data: dict[str, JsonValue] = {"completed": []}
        await store.save_execution_state("run-system-only", state_data)

        # Run with only artifacts
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save_artifact("run-artifacts-only", "findings", message)

        run_ids = await store.list_runs()

        assert "run-system-only" in run_ids
        assert "run-artifacts-only" in run_ids
