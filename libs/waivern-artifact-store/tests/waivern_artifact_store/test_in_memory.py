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
# System Data Tests
# =============================================================================


class TestAsyncInMemoryStoreSaveSystemData:
    """Tests for the save_system_data() method."""

    async def test_save_system_data_stores_data_retrievable_by_load(self) -> None:
        store = AsyncInMemoryStore()
        state_data: dict[str, JsonValue] = {
            "run_id": "test-run",
            "completed": ["artifact_a"],
            "failed": [],
            "skipped": [],
            "not_started": ["artifact_b"],
        }

        await store.save_system_data("test-run", "state", state_data)

        loaded = await store.load_system_data("test-run", "state")
        assert loaded["run_id"] == "test-run"
        assert loaded["completed"] == ["artifact_a"]

    async def test_save_system_data_overwrites_existing(self) -> None:
        store = AsyncInMemoryStore()
        original: dict[str, JsonValue] = {"status": "running", "completed_at": None}
        updated: dict[str, JsonValue] = {
            "status": "completed",
            "completed_at": "2024-01-15T11:00:00Z",
        }

        await store.save_system_data("test-run", "metadata", original)
        await store.save_system_data("test-run", "metadata", updated)

        loaded = await store.load_system_data("test-run", "metadata")
        assert loaded["status"] == "completed"
        assert loaded["completed_at"] == "2024-01-15T11:00:00Z"


class TestAsyncInMemoryStoreLoadSystemData:
    """Tests for the load_system_data() method."""

    async def test_load_system_data_returns_saved_data(self) -> None:
        store = AsyncInMemoryStore()
        metadata: dict[str, JsonValue] = {
            "run_id": "test-run",
            "runbook_path": "/path/to/runbook.yaml",
            "status": "completed",
            "started_at": "2024-01-15T10:00:00Z",
            "completed_at": "2024-01-15T10:30:00Z",
        }
        await store.save_system_data("test-run", "metadata", metadata)

        loaded = await store.load_system_data("test-run", "metadata")

        assert loaded["run_id"] == "test-run"
        assert loaded["status"] == "completed"

    async def test_load_system_data_raises_not_found_for_missing_key(self) -> None:
        store = AsyncInMemoryStore()

        with pytest.raises(ArtifactNotFoundError):
            await store.load_system_data("test-run", "nonexistent")

    async def test_load_system_data_raises_not_found_for_missing_run(self) -> None:
        store = AsyncInMemoryStore()

        with pytest.raises(ArtifactNotFoundError):
            await store.load_system_data("nonexistent-run", "metadata")


class TestAsyncInMemoryStoreSystemDataExists:
    """Tests for the system_data_exists() method."""

    async def test_system_data_exists_returns_true_after_save(self) -> None:
        store = AsyncInMemoryStore()
        data: dict[str, JsonValue] = {"status": "running"}
        await store.save_system_data("test-run", "metadata", data)

        assert await store.system_data_exists("test-run", "metadata") is True

    async def test_system_data_exists_returns_false_for_unsaved(self) -> None:
        store = AsyncInMemoryStore()

        assert await store.system_data_exists("test-run", "metadata") is False

    async def test_system_data_exists_returns_false_for_wrong_key(self) -> None:
        store = AsyncInMemoryStore()
        data: dict[str, JsonValue] = {"status": "running"}
        await store.save_system_data("test-run", "metadata", data)

        assert await store.system_data_exists("test-run", "state") is False


class TestAsyncInMemoryStoreSystemDataKeyIsolation:
    """Tests for key isolation within system data."""

    async def test_different_keys_do_not_interfere(self) -> None:
        store = AsyncInMemoryStore()
        state: dict[str, JsonValue] = {"completed": ["a"]}
        metadata: dict[str, JsonValue] = {"status": "running"}
        plan: dict[str, JsonValue] = {"runbook": {"name": "test"}}

        await store.save_system_data("test-run", "state", state)
        await store.save_system_data("test-run", "metadata", metadata)
        await store.save_system_data("test-run", "plan", plan)

        loaded_state = await store.load_system_data("test-run", "state")
        loaded_metadata = await store.load_system_data("test-run", "metadata")
        loaded_plan = await store.load_system_data("test-run", "plan")

        assert loaded_state["completed"] == ["a"]
        assert loaded_metadata["status"] == "running"
        assert loaded_plan["runbook"] == {"name": "test"}


# =============================================================================
# System Data Isolation Tests
# =============================================================================


class TestAsyncInMemoryStoreSystemDataIsolation:
    """Tests for isolation between artifacts and system data."""

    async def test_system_data_isolated_from_artifacts(self) -> None:
        """System data should not appear in artifact listings."""
        store = AsyncInMemoryStore()

        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save_artifact("test-run", "findings", message)
        state_data: dict[str, JsonValue] = {"completed": []}
        metadata: dict[str, JsonValue] = {"status": "running"}
        await store.save_system_data("test-run", "state", state_data)
        await store.save_system_data("test-run", "metadata", metadata)

        artifact_ids = await store.list_artifacts("test-run")

        assert artifact_ids == ["findings"]

    async def test_clear_artifacts_preserves_system_data(self) -> None:
        """clear_artifacts() should preserve system data."""
        store = AsyncInMemoryStore()

        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save_artifact("test-run", "findings", message)
        state_data: dict[str, JsonValue] = {"completed": ["findings"]}
        metadata: dict[str, JsonValue] = {"status": "completed"}
        await store.save_system_data("test-run", "state", state_data)
        await store.save_system_data("test-run", "metadata", metadata)

        await store.clear_artifacts("test-run")

        assert await store.list_artifacts("test-run") == []
        state = await store.load_system_data("test-run", "state")
        assert state["completed"] == ["findings"]
        loaded_meta = await store.load_system_data("test-run", "metadata")
        assert loaded_meta["status"] == "completed"

    async def test_system_data_isolated_between_runs(self) -> None:
        """System data should be isolated between different runs."""
        store = AsyncInMemoryStore()

        state_1: dict[str, JsonValue] = {"completed": ["a"]}
        state_2: dict[str, JsonValue] = {"completed": ["b", "c"]}
        await store.save_system_data("run-1", "state", state_1)
        await store.save_system_data("run-2", "state", state_2)

        loaded_1 = await store.load_system_data("run-1", "state")
        loaded_2 = await store.load_system_data("run-2", "state")

        assert loaded_1["completed"] == ["a"]
        assert loaded_2["completed"] == ["b", "c"]

    async def test_list_runs_includes_runs_with_only_system_data(self) -> None:
        """list_runs() should include runs that only have system data."""
        store = AsyncInMemoryStore()

        state_data: dict[str, JsonValue] = {"completed": []}
        await store.save_system_data("run-system-only", "state", state_data)

        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save_artifact("run-artifacts-only", "findings", message)

        run_ids = await store.list_runs()

        assert "run-system-only" in run_ids
        assert "run-artifacts-only" in run_ids


# =============================================================================
# LLM Cache Tests
# =============================================================================


class TestAsyncInMemoryStoreCacheSet:
    """Tests for the cache_set() method."""

    async def test_cache_set_stores_entry_retrievable_by_cache_get(self) -> None:
        store = AsyncInMemoryStore()
        entry: dict[str, JsonValue] = {
            "status": "completed",
            "response": {"result": "test-value"},
            "batch_id": None,
        }

        await store.cache_set("test-run", "abc123", entry)

        retrieved = await store.cache_get("test-run", "abc123")
        assert retrieved is not None
        assert retrieved["status"] == "completed"
        assert retrieved["response"] == {"result": "test-value"}

    async def test_cache_set_overwrites_existing_entry(self) -> None:
        store = AsyncInMemoryStore()
        original: dict[str, JsonValue] = {"status": "pending", "response": None}
        updated: dict[str, JsonValue] = {
            "status": "completed",
            "response": {"result": "done"},
        }

        await store.cache_set("test-run", "key1", original)
        await store.cache_set("test-run", "key1", updated)

        retrieved = await store.cache_get("test-run", "key1")
        assert retrieved is not None
        assert retrieved["status"] == "completed"
        assert retrieved["response"] == {"result": "done"}


class TestAsyncInMemoryStoreCacheGet:
    """Tests for the cache_get() method."""

    async def test_cache_get_returns_none_for_missing_entry(self) -> None:
        store = AsyncInMemoryStore()

        result = await store.cache_get("test-run", "nonexistent")

        assert result is None


class TestAsyncInMemoryStoreCacheDelete:
    """Tests for the cache_delete() method."""

    async def test_cache_delete_removes_entry(self) -> None:
        store = AsyncInMemoryStore()
        entry: dict[str, JsonValue] = {"status": "completed", "response": {"data": "x"}}
        await store.cache_set("test-run", "key1", entry)
        assert await store.cache_get("test-run", "key1") is not None

        await store.cache_delete("test-run", "key1")

        assert await store.cache_get("test-run", "key1") is None

    async def test_cache_delete_does_not_raise_for_missing(self) -> None:
        store = AsyncInMemoryStore()

        # Should not raise any exception
        await store.cache_delete("test-run", "nonexistent")


class TestAsyncInMemoryStoreCacheClear:
    """Tests for the cache_clear() method."""

    async def test_cache_clear_removes_all_cache_entries(self) -> None:
        store = AsyncInMemoryStore()
        for key in ["key1", "key2", "key3"]:
            entry: dict[str, JsonValue] = {"status": "completed", "key": key}
            await store.cache_set("test-run", key, entry)

        await store.cache_clear("test-run")

        assert await store.cache_get("test-run", "key1") is None
        assert await store.cache_get("test-run", "key2") is None
        assert await store.cache_get("test-run", "key3") is None

    async def test_cache_clear_does_not_affect_artifacts(self) -> None:
        store = AsyncInMemoryStore()
        # Save an artifact
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save_artifact("test-run", "findings", message)
        # Save a cache entry
        entry: dict[str, JsonValue] = {"status": "completed"}
        await store.cache_set("test-run", "cache-key", entry)

        await store.cache_clear("test-run")

        # Artifact should still exist
        assert await store.artifact_exists("test-run", "findings")
        # Cache should be cleared
        assert await store.cache_get("test-run", "cache-key") is None

    async def test_cache_clear_does_not_affect_system_data(self) -> None:
        store = AsyncInMemoryStore()
        state_data: dict[str, JsonValue] = {"completed": ["a"]}
        metadata: dict[str, JsonValue] = {"status": "running"}
        await store.save_system_data("test-run", "state", state_data)
        await store.save_system_data("test-run", "metadata", metadata)
        entry: dict[str, JsonValue] = {"status": "completed"}
        await store.cache_set("test-run", "cache-key", entry)

        await store.cache_clear("test-run")

        state = await store.load_system_data("test-run", "state")
        assert state["completed"] == ["a"]
        run_meta = await store.load_system_data("test-run", "metadata")
        assert run_meta["status"] == "running"
        assert await store.cache_get("test-run", "cache-key") is None


class TestAsyncInMemoryStoreCacheIsolation:
    """Tests for cache isolation between runs."""

    async def test_cache_entries_isolated_between_runs(self) -> None:
        store = AsyncInMemoryStore()
        entry_run1: dict[str, JsonValue] = {"status": "completed", "run": "1"}
        entry_run2: dict[str, JsonValue] = {"status": "pending", "run": "2"}

        await store.cache_set("run-1", "same-key", entry_run1)
        await store.cache_set("run-2", "same-key", entry_run2)

        retrieved_run1 = await store.cache_get("run-1", "same-key")
        retrieved_run2 = await store.cache_get("run-2", "same-key")

        assert retrieved_run1 is not None
        assert retrieved_run1["run"] == "1"
        assert retrieved_run2 is not None
        assert retrieved_run2["run"] == "2"


# =============================================================================
# Batch Job Tests
# =============================================================================


class TestAsyncInMemoryStoreSaveBatchJob:
    """Tests for the save_batch_job() method."""

    async def test_save_batch_job_stores_data_retrievable_by_load(self) -> None:
        store = AsyncInMemoryStore()
        data: dict[str, JsonValue] = {
            "batch_id": "batch-123",
            "status": "submitted",
            "cache_keys": ["key-a", "key-b"],
        }

        await store.save_batch_job("test-run", "batch-123", data)

        retrieved = await store.load_batch_job("test-run", "batch-123")
        assert retrieved["batch_id"] == "batch-123"
        assert retrieved["status"] == "submitted"
        assert retrieved["cache_keys"] == ["key-a", "key-b"]

    async def test_save_batch_job_overwrites_existing(self) -> None:
        store = AsyncInMemoryStore()
        original: dict[str, JsonValue] = {"status": "submitted", "request_count": 3}
        updated: dict[str, JsonValue] = {"status": "completed", "request_count": 3}

        await store.save_batch_job("test-run", "batch-1", original)
        await store.save_batch_job("test-run", "batch-1", updated)

        retrieved = await store.load_batch_job("test-run", "batch-1")
        assert retrieved["status"] == "completed"


class TestAsyncInMemoryStoreLoadBatchJob:
    """Tests for the load_batch_job() method."""

    async def test_load_batch_job_raises_not_found_for_missing(self) -> None:
        store = AsyncInMemoryStore()

        with pytest.raises(ArtifactNotFoundError, match="batch-nonexistent"):
            await store.load_batch_job("test-run", "batch-nonexistent")


class TestAsyncInMemoryStoreListBatchJobs:
    """Tests for the list_batch_jobs() method."""

    async def test_list_batch_jobs_returns_all_saved_ids(self) -> None:
        store = AsyncInMemoryStore()
        for batch_id in ["batch-a", "batch-b", "batch-c"]:
            data: dict[str, JsonValue] = {"batch_id": batch_id, "status": "submitted"}
            await store.save_batch_job("test-run", batch_id, data)

        result = await store.list_batch_jobs("test-run")

        assert result == ["batch-a", "batch-b", "batch-c"]

    async def test_list_batch_jobs_returns_empty_for_no_batch_jobs(self) -> None:
        store = AsyncInMemoryStore()

        result = await store.list_batch_jobs("test-run")

        assert result == []


class TestAsyncInMemoryStoreBatchJobIsolation:
    """Tests for batch job isolation between runs and storage domains."""

    async def test_batch_jobs_isolated_between_runs(self) -> None:
        store = AsyncInMemoryStore()
        data_run1: dict[str, JsonValue] = {"status": "submitted", "run": "1"}
        data_run2: dict[str, JsonValue] = {"status": "completed", "run": "2"}

        await store.save_batch_job("run-1", "same-batch", data_run1)
        await store.save_batch_job("run-2", "same-batch", data_run2)

        retrieved_run1 = await store.load_batch_job("run-1", "same-batch")
        retrieved_run2 = await store.load_batch_job("run-2", "same-batch")
        assert retrieved_run1["run"] == "1"
        assert retrieved_run2["run"] == "2"

    async def test_clear_artifacts_preserves_batch_jobs(self) -> None:
        store = AsyncInMemoryStore()
        # Save an artifact and a batch job
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save_artifact("test-run", "findings", message)
        data: dict[str, JsonValue] = {"batch_id": "batch-1", "status": "submitted"}
        await store.save_batch_job("test-run", "batch-1", data)

        await store.clear_artifacts("test-run")

        # Batch job should still exist
        retrieved = await store.load_batch_job("test-run", "batch-1")
        assert retrieved["status"] == "submitted"
        # Artifact should be gone
        assert not await store.artifact_exists("test-run", "findings")

    async def test_list_artifacts_excludes_batch_jobs(self) -> None:
        store = AsyncInMemoryStore()
        # Save a batch job and an artifact
        data: dict[str, JsonValue] = {"batch_id": "batch-1", "status": "submitted"}
        await store.save_batch_job("test-run", "batch-1", data)
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save_artifact("test-run", "findings", message)

        artifacts = await store.list_artifacts("test-run")

        assert artifacts == ["findings"]


# =============================================================================
# Prepared State Tests
# =============================================================================


class TestAsyncInMemoryStoreSavePrepared:
    """Tests for the save_prepared() method."""

    async def test_save_prepared_stores_data_retrievable_by_load(self) -> None:
        store = AsyncInMemoryStore()
        data: dict[str, JsonValue] = {
            "state": {"findings_count": 5},
            "requests": {"validation": {"run_id": "run-1"}},
        }

        await store.save_prepared("test-run", "personal-data", data)

        retrieved = await store.load_prepared("test-run", "personal-data")
        assert retrieved["state"] == {"findings_count": 5}
        assert retrieved["requests"] == {"validation": {"run_id": "run-1"}}

    async def test_save_prepared_overwrites_existing(self) -> None:
        store = AsyncInMemoryStore()
        original: dict[str, JsonValue] = {"state": {"status": "initial"}}
        updated: dict[str, JsonValue] = {"state": {"status": "updated"}}

        await store.save_prepared("test-run", "artifact-1", original)
        await store.save_prepared("test-run", "artifact-1", updated)

        retrieved = await store.load_prepared("test-run", "artifact-1")
        assert retrieved["state"] == {"status": "updated"}


class TestAsyncInMemoryStoreLoadPrepared:
    """Tests for the load_prepared() method."""

    async def test_load_prepared_raises_not_found_for_missing(self) -> None:
        store = AsyncInMemoryStore()

        with pytest.raises(ArtifactNotFoundError, match="nonexistent"):
            await store.load_prepared("test-run", "nonexistent")


class TestAsyncInMemoryStoreDeletePrepared:
    """Tests for the delete_prepared() method."""

    async def test_delete_prepared_removes_saved(self) -> None:
        store = AsyncInMemoryStore()
        data: dict[str, JsonValue] = {"state": {"status": "pending"}}
        await store.save_prepared("test-run", "artifact-1", data)

        await store.delete_prepared("test-run", "artifact-1")

        assert not await store.prepared_exists("test-run", "artifact-1")

    async def test_delete_prepared_does_not_raise_for_missing(self) -> None:
        store = AsyncInMemoryStore()

        await store.delete_prepared("test-run", "nonexistent")


class TestAsyncInMemoryStorePreparedExists:
    """Tests for the prepared_exists() method."""

    async def test_prepared_exists_returns_true_after_save(self) -> None:
        store = AsyncInMemoryStore()
        data: dict[str, JsonValue] = {"state": {"status": "pending"}}
        await store.save_prepared("test-run", "artifact-1", data)

        assert await store.prepared_exists("test-run", "artifact-1")

    async def test_prepared_exists_returns_false_for_unsaved(self) -> None:
        store = AsyncInMemoryStore()

        assert not await store.prepared_exists("test-run", "nonexistent")


class TestAsyncInMemoryStorePreparedIsolation:
    """Tests for prepared data isolation between runs and storage domains."""

    async def test_prepared_data_isolated_between_runs(self) -> None:
        store = AsyncInMemoryStore()
        data_run1: dict[str, JsonValue] = {"state": {"run": "1"}}
        data_run2: dict[str, JsonValue] = {"state": {"run": "2"}}

        await store.save_prepared("run-1", "same-artifact", data_run1)
        await store.save_prepared("run-2", "same-artifact", data_run2)

        retrieved_run1 = await store.load_prepared("run-1", "same-artifact")
        retrieved_run2 = await store.load_prepared("run-2", "same-artifact")
        assert retrieved_run1["state"] == {"run": "1"}
        assert retrieved_run2["state"] == {"run": "2"}

    async def test_clear_artifacts_preserves_prepared_data(self) -> None:
        store = AsyncInMemoryStore()
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save_artifact("test-run", "findings", message)
        data: dict[str, JsonValue] = {"state": {"status": "pending"}}
        await store.save_prepared("test-run", "artifact-1", data)

        await store.clear_artifacts("test-run")

        retrieved = await store.load_prepared("test-run", "artifact-1")
        assert retrieved["state"] == {"status": "pending"}
        assert not await store.artifact_exists("test-run", "findings")

    async def test_list_artifacts_excludes_prepared_data(self) -> None:
        store = AsyncInMemoryStore()
        data: dict[str, JsonValue] = {"state": {"status": "pending"}}
        await store.save_prepared("test-run", "artifact-1", data)
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save_artifact("test-run", "findings", message)

        artifacts = await store.list_artifacts("test-run")

        assert artifacts == ["findings"]
