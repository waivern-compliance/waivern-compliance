"""Tests for LocalFilesystemStore implementation."""

import json
from pathlib import Path

import pytest
from waivern_core.message import Message
from waivern_core.schemas import Schema

from waivern_artifact_store.errors import ArtifactNotFoundError
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
