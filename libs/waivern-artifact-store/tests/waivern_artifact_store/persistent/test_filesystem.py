"""Tests for LocalFilesystemStore implementation."""

import json
from pathlib import Path

import pytest
from waivern_core.message import Message
from waivern_core.schemas import Schema

from waivern_artifact_store.errors import ArtifactNotFoundError
from waivern_artifact_store.persistent.filesystem import LocalFilesystemStore

# =============================================================================
# Save Tests (file creation, directory handling, upsert semantics)
# =============================================================================


class TestLocalFilesystemStoreSave:
    """Tests for the save() method."""

    async def test_save_creates_file_with_message_content(self, tmp_path: Path) -> None:
        store = LocalFilesystemStore(run_id="test-run", base_path=tmp_path)
        message = Message(
            id="msg-1",
            content={"data": "test-value"},
            schema=Schema("test_schema", "1.0.0"),
        )

        await store.save("my_artifact", message)

        expected_path = tmp_path / "runs" / "test-run" / "my_artifact.json"
        assert expected_path.exists()
        with expected_path.open() as f:
            saved_data = json.load(f)
        assert saved_data["id"] == "msg-1"
        assert saved_data["content"] == {"data": "test-value"}

    async def test_save_with_hierarchical_key_creates_nested_structure(
        self, tmp_path: Path
    ) -> None:
        store = LocalFilesystemStore(run_id="test-run", base_path=tmp_path)
        message = Message(
            id="msg-1",
            content={"findings": []},
            schema=Schema("test_schema", "1.0.0"),
        )

        await store.save("artifacts/findings", message)

        expected_path = tmp_path / "runs" / "test-run" / "artifacts" / "findings.json"
        assert expected_path.exists()
        assert expected_path.parent.is_dir()

    async def test_save_overwrites_existing_artifact(self, tmp_path: Path) -> None:
        store = LocalFilesystemStore(run_id="test-run", base_path=tmp_path)
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

        await store.save("artifact", original_message)
        await store.save("artifact", updated_message)

        file_path = tmp_path / "runs" / "test-run" / "artifact.json"
        with file_path.open() as f:
            saved_data = json.load(f)
        assert saved_data["id"] == "msg-2"
        assert saved_data["content"] == {"version": "updated"}


# =============================================================================
# Get Tests (retrieval and error handling)
# =============================================================================


class TestLocalFilesystemStoreGet:
    """Tests for the get() method."""

    async def test_get_returns_previously_saved_message(self, tmp_path: Path) -> None:
        store = LocalFilesystemStore(run_id="test-run", base_path=tmp_path)
        original = Message(
            id="msg-1",
            content={"data": "test-value"},
            schema=Schema("test_schema", "1.0.0"),
            run_id="run-123",
            source="connector:test",
        )
        await store.save("artifact", original)

        retrieved = await store.get("artifact")

        assert retrieved.id == original.id
        assert retrieved.content == original.content
        assert retrieved.run_id == original.run_id
        assert retrieved.source == original.source

    async def test_get_raises_artifact_not_found_for_missing_key(
        self, tmp_path: Path
    ) -> None:
        store = LocalFilesystemStore(run_id="test-run", base_path=tmp_path)

        with pytest.raises(ArtifactNotFoundError):
            await store.get("nonexistent")


# =============================================================================
# Exists Tests (presence checking)
# =============================================================================


class TestLocalFilesystemStoreExists:
    """Tests for the exists() method."""

    async def test_exists_returns_true_after_save(self, tmp_path: Path) -> None:
        store = LocalFilesystemStore(run_id="test-run", base_path=tmp_path)
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save("artifact", message)

        result = await store.exists("artifact")

        assert result is True

    async def test_exists_returns_false_for_unsaved_key(self, tmp_path: Path) -> None:
        store = LocalFilesystemStore(run_id="test-run", base_path=tmp_path)

        result = await store.exists("nonexistent")

        assert result is False


# =============================================================================
# Delete Tests (removal and idempotency)
# =============================================================================


class TestLocalFilesystemStoreDelete:
    """Tests for the delete() method."""

    async def test_delete_removes_saved_artifact(self, tmp_path: Path) -> None:
        store = LocalFilesystemStore(run_id="test-run", base_path=tmp_path)
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save("artifact", message)
        assert await store.exists("artifact")

        await store.delete("artifact")

        assert not await store.exists("artifact")

    async def test_delete_does_not_raise_for_missing_key(self, tmp_path: Path) -> None:
        store = LocalFilesystemStore(run_id="test-run", base_path=tmp_path)

        # Should not raise any exception
        await store.delete("nonexistent")


# =============================================================================
# List Keys Tests (enumeration and filtering)
# =============================================================================


class TestLocalFilesystemStoreListKeys:
    """Tests for the list_keys() method."""

    async def test_list_keys_returns_all_saved_keys(self, tmp_path: Path) -> None:
        store = LocalFilesystemStore(run_id="test-run", base_path=tmp_path)
        for key in ["alpha", "beta", "gamma"]:
            message = Message(
                id=f"msg-{key}",
                content={"key": key},
                schema=Schema("test_schema", "1.0.0"),
            )
            await store.save(key, message)

        keys = await store.list_keys()

        assert set(keys) == {"alpha", "beta", "gamma"}

    async def test_list_keys_with_prefix_filters_results(self, tmp_path: Path) -> None:
        store = LocalFilesystemStore(run_id="test-run", base_path=tmp_path)
        for key in ["artifacts/a", "artifacts/b", "cache/x"]:
            message = Message(
                id=f"msg-{key}",
                content={"key": key},
                schema=Schema("test_schema", "1.0.0"),
            )
            await store.save(key, message)

        keys = await store.list_keys(prefix="artifacts")

        assert set(keys) == {"artifacts/a", "artifacts/b"}

    async def test_list_keys_preserves_hierarchical_key_format(
        self, tmp_path: Path
    ) -> None:
        store = LocalFilesystemStore(run_id="test-run", base_path=tmp_path)
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save("deeply/nested/artifact", message)

        keys = await store.list_keys()

        assert "deeply/nested/artifact" in keys

    async def test_list_keys_excludes_system_files(self, tmp_path: Path) -> None:
        store = LocalFilesystemStore(run_id="test-run", base_path=tmp_path)
        # Save a regular artifact
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save("artifacts/findings", message)

        # Manually create a system file (simulating future state persistence)
        system_dir = tmp_path / "runs" / "test-run" / "_system"
        system_dir.mkdir(parents=True)
        (system_dir / "metadata.json").write_text('{"status": "running"}')

        keys = await store.list_keys()

        assert "artifacts/findings" in keys
        assert "_system/metadata" not in keys


# =============================================================================
# Clear Tests (bulk removal)
# =============================================================================


class TestLocalFilesystemStoreClear:
    """Tests for the clear() method."""

    async def test_clear_removes_all_artifacts(self, tmp_path: Path) -> None:
        store = LocalFilesystemStore(run_id="test-run", base_path=tmp_path)
        for key in ["alpha", "beta", "nested/gamma"]:
            message = Message(
                id=f"msg-{key}",
                content={"key": key},
                schema=Schema("test_schema", "1.0.0"),
            )
            await store.save(key, message)
        assert len(await store.list_keys()) == 3

        await store.clear()

        assert await store.list_keys() == []


# =============================================================================
# Key Validation Tests (security)
# =============================================================================


class TestLocalFilesystemStoreKeyValidation:
    """Tests for key validation (security)."""

    @pytest.mark.parametrize(
        "invalid_key",
        [
            "../etc/passwd",
            "foo/../bar",
            "/absolute/path",
            "valid/../../escape",
        ],
    )
    async def test_save_rejects_invalid_keys(
        self, tmp_path: Path, invalid_key: str
    ) -> None:
        store = LocalFilesystemStore(run_id="test-run", base_path=tmp_path)
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )

        with pytest.raises(ValueError, match="Invalid key"):
            await store.save(invalid_key, message)

    @pytest.mark.parametrize(
        "invalid_key",
        [
            "../etc/passwd",
            "foo/../bar",
            "/absolute/path",
        ],
    )
    async def test_get_rejects_invalid_keys(
        self, tmp_path: Path, invalid_key: str
    ) -> None:
        store = LocalFilesystemStore(run_id="test-run", base_path=tmp_path)

        with pytest.raises(ValueError, match="Invalid key"):
            await store.get(invalid_key)
