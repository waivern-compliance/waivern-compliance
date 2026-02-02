"""Tests for LocalFilesystemStore implementation."""

import json
from pathlib import Path

import pytest
from waivern_core import JsonValue
from waivern_core.message import Message
from waivern_core.schemas import Schema

from waivern_artifact_store.errors import ArtifactNotFoundError, ArtifactStoreError
from waivern_artifact_store.filesystem import LocalFilesystemStore

# =============================================================================
# Save Artifact Tests
# =============================================================================


class TestLocalFilesystemStoreSaveArtifact:
    """Tests for the save_artifact() method."""

    async def test_save_artifact_creates_file_in_artifacts_subdirectory(
        self, tmp_path: Path
    ) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
        message = Message(
            id="msg-1",
            content={"data": "test-value"},
            schema=Schema("test_schema", "1.0.0"),
        )

        await store.save_artifact("test-run", "my_artifact", message)

        expected_path = (
            tmp_path / "runs" / "test-run" / "artifacts" / "my_artifact.json"
        )
        assert expected_path.exists()
        with expected_path.open() as f:
            saved_data = json.load(f)
        assert saved_data["id"] == "msg-1"
        assert saved_data["content"] == {"data": "test-value"}

    async def test_save_artifact_with_nested_id_creates_nested_structure(
        self, tmp_path: Path
    ) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
        message = Message(
            id="msg-1",
            content={"findings": []},
            schema=Schema("test_schema", "1.0.0"),
        )

        await store.save_artifact("test-run", "namespace/findings", message)

        expected_path = (
            tmp_path / "runs" / "test-run" / "artifacts" / "namespace" / "findings.json"
        )
        assert expected_path.exists()
        assert expected_path.parent.is_dir()

    async def test_save_artifact_overwrites_existing(self, tmp_path: Path) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
        original_message = Message(
            id="msg-1",
            content={"version": "original"},
            schema=Schema("test_schema", "1.0.0"),
        )
        updated_message = Message(
            id="msg-2",
            content={"version": "updated"},
            schema=Schema("test_schema", "1.0.0"),
        )

        await store.save_artifact("test-run", "artifact", original_message)
        await store.save_artifact("test-run", "artifact", updated_message)

        file_path = tmp_path / "runs" / "test-run" / "artifacts" / "artifact.json"
        with file_path.open() as f:
            saved_data = json.load(f)
        assert saved_data["id"] == "msg-2"
        assert saved_data["content"] == {"version": "updated"}


# =============================================================================
# Get Artifact Tests
# =============================================================================


class TestLocalFilesystemStoreGetArtifact:
    """Tests for the get_artifact() method."""

    async def test_get_artifact_returns_previously_saved_message(
        self, tmp_path: Path
    ) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
        original = Message(
            id="msg-1",
            content={"data": "test-value"},
            schema=Schema("test_schema", "1.0.0"),
            run_id="run-123",
            source="connector:test",
        )
        await store.save_artifact("test-run", "artifact", original)

        retrieved = await store.get_artifact("test-run", "artifact")

        assert retrieved.id == original.id
        assert retrieved.content == original.content
        assert retrieved.run_id == original.run_id
        assert retrieved.source == original.source

    async def test_get_artifact_raises_not_found_for_missing(
        self, tmp_path: Path
    ) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)

        with pytest.raises(ArtifactNotFoundError):
            await store.get_artifact("test-run", "nonexistent")


# =============================================================================
# Artifact Exists Tests
# =============================================================================


class TestLocalFilesystemStoreArtifactExists:
    """Tests for the artifact_exists() method."""

    async def test_artifact_exists_returns_true_after_save(
        self, tmp_path: Path
    ) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save_artifact("test-run", "artifact", message)

        result = await store.artifact_exists("test-run", "artifact")

        assert result is True

    async def test_artifact_exists_returns_false_for_unsaved(
        self, tmp_path: Path
    ) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)

        result = await store.artifact_exists("test-run", "nonexistent")

        assert result is False


# =============================================================================
# Delete Artifact Tests
# =============================================================================


class TestLocalFilesystemStoreDeleteArtifact:
    """Tests for the delete_artifact() method."""

    async def test_delete_artifact_removes_saved(self, tmp_path: Path) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save_artifact("test-run", "artifact", message)
        assert await store.artifact_exists("test-run", "artifact")

        await store.delete_artifact("test-run", "artifact")

        assert not await store.artifact_exists("test-run", "artifact")

    async def test_delete_artifact_does_not_raise_for_missing(
        self, tmp_path: Path
    ) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)

        # Should not raise any exception
        await store.delete_artifact("test-run", "nonexistent")


# =============================================================================
# List Artifacts Tests
# =============================================================================


class TestLocalFilesystemStoreListArtifacts:
    """Tests for the list_artifacts() method."""

    async def test_list_artifacts_returns_all_saved_ids(self, tmp_path: Path) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
        for artifact_id in ["alpha", "beta", "gamma"]:
            message = Message(
                id=f"msg-{artifact_id}",
                content={"key": artifact_id},
                schema=Schema("test_schema", "1.0.0"),
            )
            await store.save_artifact("test-run", artifact_id, message)

        artifact_ids = await store.list_artifacts("test-run")

        assert set(artifact_ids) == {"alpha", "beta", "gamma"}

    async def test_list_artifacts_returns_nested_ids_without_prefix(
        self, tmp_path: Path
    ) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save_artifact("test-run", "deeply/nested/artifact", message)

        artifact_ids = await store.list_artifacts("test-run")

        assert "deeply/nested/artifact" in artifact_ids

    async def test_list_artifacts_excludes_system_files(self, tmp_path: Path) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
        # Save a regular artifact
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save_artifact("test-run", "findings", message)

        # Manually create a system file (simulating state persistence)
        system_dir = tmp_path / "runs" / "test-run" / "_system"
        system_dir.mkdir(parents=True)
        (system_dir / "state.json").write_text('{"status": "running"}')

        artifact_ids = await store.list_artifacts("test-run")

        assert "findings" in artifact_ids
        assert "state" not in artifact_ids
        assert "_system/state" not in artifact_ids

    async def test_list_artifacts_returns_empty_for_no_artifacts(
        self, tmp_path: Path
    ) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)

        artifact_ids = await store.list_artifacts("test-run")

        assert artifact_ids == []


# =============================================================================
# Clear Artifacts Tests
# =============================================================================


class TestLocalFilesystemStoreClearArtifacts:
    """Tests for the clear_artifacts() method."""

    async def test_clear_artifacts_removes_all_artifacts(self, tmp_path: Path) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
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

    async def test_clear_artifacts_preserves_system_metadata(
        self, tmp_path: Path
    ) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
        # Save an artifact
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save_artifact("test-run", "artifact", message)

        # Manually create system metadata
        system_dir = tmp_path / "runs" / "test-run" / "_system"
        system_dir.mkdir(parents=True)
        (system_dir / "state.json").write_text('{"status": "completed"}')

        await store.clear_artifacts("test-run")

        # System metadata should still exist
        assert (system_dir / "state.json").exists()
        assert not await store.artifact_exists("test-run", "artifact")


# =============================================================================
# Run Isolation Tests
# =============================================================================


class TestLocalFilesystemStoreRunIsolation:
    """Tests for run isolation in singleton store."""

    async def test_different_runs_have_isolated_storage(self, tmp_path: Path) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
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

        # Verify files are in separate directories
        assert (tmp_path / "runs" / "run-1" / "artifacts" / "artifact.json").exists()
        assert (tmp_path / "runs" / "run-2" / "artifacts" / "artifact.json").exists()

    async def test_clear_artifacts_only_affects_specified_run(
        self, tmp_path: Path
    ) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
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


class TestLocalFilesystemStoreListRuns:
    """Tests for the list_runs() method."""

    async def test_list_runs_returns_all_run_ids(self, tmp_path: Path) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
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

    async def test_list_runs_returns_empty_for_no_runs(self, tmp_path: Path) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)

        run_ids = await store.list_runs()

        assert run_ids == []


# =============================================================================
# Execution State Tests
# =============================================================================


class TestLocalFilesystemStoreSaveExecutionState:
    """Tests for the save_execution_state() method."""

    async def test_save_execution_state_creates_file_in_system_directory(
        self, tmp_path: Path
    ) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
        state_data: dict[str, JsonValue] = {
            "run_id": "test-run",
            "completed": ["artifact_a"],
            "failed": [],
            "skipped": [],
            "not_started": ["artifact_b"],
        }

        await store.save_execution_state("test-run", state_data)

        expected_path = tmp_path / "runs" / "test-run" / "_system" / "state.json"
        assert expected_path.exists()
        with expected_path.open() as f:
            saved_data = json.load(f)
        assert saved_data["run_id"] == "test-run"
        assert saved_data["completed"] == ["artifact_a"]

    async def test_save_execution_state_overwrites_existing(
        self, tmp_path: Path
    ) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
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


class TestLocalFilesystemStoreLoadExecutionState:
    """Tests for the load_execution_state() method."""

    async def test_load_execution_state_returns_saved_data(
        self, tmp_path: Path
    ) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
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

    async def test_load_execution_state_raises_not_found_for_missing(
        self, tmp_path: Path
    ) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)

        with pytest.raises(ArtifactNotFoundError) as exc_info:
            await store.load_execution_state("nonexistent-run")

        assert "Execution state not found" in str(exc_info.value)

    async def test_load_execution_state_raises_error_for_invalid_format(
        self, tmp_path: Path
    ) -> None:
        """Loading non-dict JSON should raise ArtifactStoreError."""
        store = LocalFilesystemStore(base_path=tmp_path)

        # Manually create invalid state file (array instead of dict)
        system_dir = tmp_path / "runs" / "test-run" / "_system"
        system_dir.mkdir(parents=True)
        (system_dir / "state.json").write_text('["invalid", "format"]')

        with pytest.raises(ArtifactStoreError) as exc_info:
            await store.load_execution_state("test-run")

        assert "Invalid execution state format" in str(exc_info.value)


# =============================================================================
# Run Metadata Tests
# =============================================================================


class TestLocalFilesystemStoreSaveRunMetadata:
    """Tests for the save_run_metadata() method."""

    async def test_save_run_metadata_creates_file_in_system_directory(
        self, tmp_path: Path
    ) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
        metadata: dict[str, JsonValue] = {
            "run_id": "test-run",
            "runbook_path": "/path/to/runbook.yaml",
            "runbook_hash": "sha256:abc123",
            "status": "running",
            "started_at": "2024-01-15T10:00:00Z",
        }

        await store.save_run_metadata("test-run", metadata)

        expected_path = tmp_path / "runs" / "test-run" / "_system" / "run.json"
        assert expected_path.exists()
        with expected_path.open() as f:
            saved_data = json.load(f)
        assert saved_data["run_id"] == "test-run"
        assert saved_data["status"] == "running"

    async def test_save_run_metadata_overwrites_existing(self, tmp_path: Path) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
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


class TestLocalFilesystemStoreLoadRunMetadata:
    """Tests for the load_run_metadata() method."""

    async def test_load_run_metadata_returns_saved_data(self, tmp_path: Path) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
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

    async def test_load_run_metadata_raises_not_found_for_missing(
        self, tmp_path: Path
    ) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)

        with pytest.raises(ArtifactNotFoundError) as exc_info:
            await store.load_run_metadata("nonexistent-run")

        assert "Run metadata not found" in str(exc_info.value)

    async def test_load_run_metadata_raises_error_for_invalid_format(
        self, tmp_path: Path
    ) -> None:
        """Loading non-dict JSON should raise ArtifactStoreError."""
        store = LocalFilesystemStore(base_path=tmp_path)

        # Manually create invalid metadata file (string instead of dict)
        system_dir = tmp_path / "runs" / "test-run" / "_system"
        system_dir.mkdir(parents=True)
        (system_dir / "run.json").write_text('"just a string"')

        with pytest.raises(ArtifactStoreError) as exc_info:
            await store.load_run_metadata("test-run")

        assert "Invalid run metadata format" in str(exc_info.value)


# =============================================================================
# System Metadata Isolation Tests
# =============================================================================


class TestLocalFilesystemStoreSystemMetadataIsolation:
    """Tests for isolation between artifacts and system metadata."""

    async def test_system_metadata_isolated_from_artifacts(
        self, tmp_path: Path
    ) -> None:
        """System metadata should not appear in artifact listings."""
        store = LocalFilesystemStore(base_path=tmp_path)

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
        assert "state" not in artifact_ids
        assert "run" not in artifact_ids
        assert "_system/state" not in artifact_ids
        assert "_system/run" not in artifact_ids

    async def test_clear_artifacts_preserves_system_metadata_via_api(
        self, tmp_path: Path
    ) -> None:
        """clear_artifacts() should preserve system metadata saved via API."""
        store = LocalFilesystemStore(base_path=tmp_path)

        # Save artifacts and system metadata via API
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

    async def test_system_metadata_isolated_between_runs(self, tmp_path: Path) -> None:
        """System metadata should be isolated between different runs."""
        store = LocalFilesystemStore(base_path=tmp_path)

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


# =============================================================================
# LLM Cache Tests
# =============================================================================


class TestLocalFilesystemStoreCacheSet:
    """Tests for the cache_set() method."""

    async def test_cache_set_creates_file_in_llm_cache_subdirectory(
        self, tmp_path: Path
    ) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
        entry: dict[str, JsonValue] = {
            "status": "completed",
            "response": {"result": "test-value"},
        }

        await store.cache_set("test-run", "abc123", entry)

        expected_path = tmp_path / "runs" / "test-run" / "llm_cache" / "abc123.json"
        assert expected_path.exists()
        with expected_path.open() as f:
            saved_data = json.load(f)
        assert saved_data["status"] == "completed"
        assert saved_data["response"] == {"result": "test-value"}

    async def test_cache_set_stores_entry_retrievable_by_cache_get(
        self, tmp_path: Path
    ) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
        entry: dict[str, JsonValue] = {
            "status": "completed",
            "response": {"result": "test-value"},
            "model_name": "claude-sonnet-4-5",
        }

        await store.cache_set("test-run", "key1", entry)

        retrieved = await store.cache_get("test-run", "key1")
        assert retrieved is not None
        assert retrieved["status"] == "completed"
        assert retrieved["model_name"] == "claude-sonnet-4-5"

    async def test_cache_set_overwrites_existing_entry(self, tmp_path: Path) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
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


class TestLocalFilesystemStoreCacheGet:
    """Tests for the cache_get() method."""

    async def test_cache_get_returns_none_for_missing_entry(
        self, tmp_path: Path
    ) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)

        result = await store.cache_get("test-run", "nonexistent")

        assert result is None


class TestLocalFilesystemStoreCacheDelete:
    """Tests for the cache_delete() method."""

    async def test_cache_delete_removes_entry(self, tmp_path: Path) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
        entry: dict[str, JsonValue] = {"status": "completed"}
        await store.cache_set("test-run", "key1", entry)
        assert await store.cache_get("test-run", "key1") is not None

        await store.cache_delete("test-run", "key1")

        assert await store.cache_get("test-run", "key1") is None

    async def test_cache_delete_does_not_raise_for_missing(
        self, tmp_path: Path
    ) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)

        # Should not raise any exception
        await store.cache_delete("test-run", "nonexistent")


class TestLocalFilesystemStoreCacheClear:
    """Tests for the cache_clear() method."""

    async def test_cache_clear_removes_all_cache_entries(self, tmp_path: Path) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
        for key in ["key1", "key2", "key3"]:
            entry: dict[str, JsonValue] = {"status": "completed", "key": key}
            await store.cache_set("test-run", key, entry)

        await store.cache_clear("test-run")

        assert await store.cache_get("test-run", "key1") is None
        assert await store.cache_get("test-run", "key2") is None
        assert await store.cache_get("test-run", "key3") is None

    async def test_cache_clear_does_not_affect_artifacts(self, tmp_path: Path) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
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

    async def test_cache_clear_does_not_affect_system_metadata(
        self, tmp_path: Path
    ) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
        # Save system metadata
        state_data: dict[str, JsonValue] = {"completed": ["a"]}
        metadata: dict[str, JsonValue] = {"status": "running"}
        await store.save_execution_state("test-run", state_data)
        await store.save_run_metadata("test-run", metadata)
        # Save a cache entry
        entry: dict[str, JsonValue] = {"status": "completed"}
        await store.cache_set("test-run", "cache-key", entry)

        await store.cache_clear("test-run")

        # System metadata should still exist
        state = await store.load_execution_state("test-run")
        assert state["completed"] == ["a"]
        run_meta = await store.load_run_metadata("test-run")
        assert run_meta["status"] == "running"
        # Cache should be cleared
        assert await store.cache_get("test-run", "cache-key") is None


class TestLocalFilesystemStoreCacheIsolation:
    """Tests for cache isolation between runs."""

    async def test_cache_entries_isolated_between_runs(self, tmp_path: Path) -> None:
        store = LocalFilesystemStore(base_path=tmp_path)
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
