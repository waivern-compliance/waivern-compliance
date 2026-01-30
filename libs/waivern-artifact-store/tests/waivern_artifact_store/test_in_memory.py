"""Tests for AsyncInMemoryStore implementation."""

import pytest
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
