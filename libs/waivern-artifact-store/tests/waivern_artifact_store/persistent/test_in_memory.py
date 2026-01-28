"""Tests for AsyncInMemoryStore implementation."""

import pytest
from waivern_core.message import Message
from waivern_core.schemas import Schema

from waivern_artifact_store.errors import ArtifactNotFoundError
from waivern_artifact_store.persistent.in_memory import AsyncInMemoryStore

# =============================================================================
# Save Tests (storage and upsert semantics)
# =============================================================================


class TestAsyncInMemoryStoreSave:
    """Tests for the save() method."""

    async def test_save_stores_message_retrievable_by_get(self) -> None:
        store = AsyncInMemoryStore(run_id="test-run")
        message = Message(
            id="msg-1",
            content={"data": "test-value"},
            schema=Schema("test_schema", "1.0.0"),
        )

        await store.save("my_artifact", message)

        retrieved = await store.get("my_artifact")
        assert retrieved.id == "msg-1"
        assert retrieved.content == {"data": "test-value"}

    async def test_save_overwrites_existing_artifact(self) -> None:
        store = AsyncInMemoryStore(run_id="test-run")
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

        await store.save("artifact", original)
        await store.save("artifact", updated)

        retrieved = await store.get("artifact")
        assert retrieved.id == "msg-2"
        assert retrieved.content == {"version": "updated"}


# =============================================================================
# Get Tests (retrieval and error handling)
# =============================================================================


class TestAsyncInMemoryStoreGet:
    """Tests for the get() method."""

    async def test_get_raises_artifact_not_found_for_missing_key(self) -> None:
        store = AsyncInMemoryStore(run_id="test-run")

        with pytest.raises(ArtifactNotFoundError):
            await store.get("nonexistent")


# =============================================================================
# Exists Tests (presence checking)
# =============================================================================


class TestAsyncInMemoryStoreExists:
    """Tests for the exists() method."""

    async def test_exists_returns_true_after_save(self) -> None:
        store = AsyncInMemoryStore(run_id="test-run")
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save("artifact", message)

        result = await store.exists("artifact")

        assert result is True

    async def test_exists_returns_false_for_unsaved_key(self) -> None:
        store = AsyncInMemoryStore(run_id="test-run")

        result = await store.exists("nonexistent")

        assert result is False


# =============================================================================
# Delete Tests (removal and idempotency)
# =============================================================================


class TestAsyncInMemoryStoreDelete:
    """Tests for the delete() method."""

    async def test_delete_removes_saved_artifact(self) -> None:
        store = AsyncInMemoryStore(run_id="test-run")
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save("artifact", message)
        assert await store.exists("artifact")

        await store.delete("artifact")

        assert not await store.exists("artifact")

    async def test_delete_does_not_raise_for_missing_key(self) -> None:
        store = AsyncInMemoryStore(run_id="test-run")

        # Should not raise any exception
        await store.delete("nonexistent")


# =============================================================================
# List Keys Tests (enumeration and filtering)
# =============================================================================


class TestAsyncInMemoryStoreListKeys:
    """Tests for the list_keys() method."""

    async def test_list_keys_returns_all_saved_keys(self) -> None:
        store = AsyncInMemoryStore(run_id="test-run")
        for key in ["alpha", "beta", "gamma"]:
            message = Message(
                id=f"msg-{key}",
                content={"key": key},
                schema=Schema("test_schema", "1.0.0"),
            )
            await store.save(key, message)

        keys = await store.list_keys()

        assert set(keys) == {"alpha", "beta", "gamma"}

    async def test_list_keys_with_prefix_filters_results(self) -> None:
        store = AsyncInMemoryStore(run_id="test-run")
        for key in ["artifacts/a", "artifacts/b", "cache/x"]:
            message = Message(
                id=f"msg-{key}",
                content={"key": key},
                schema=Schema("test_schema", "1.0.0"),
            )
            await store.save(key, message)

        keys = await store.list_keys(prefix="artifacts")

        assert set(keys) == {"artifacts/a", "artifacts/b"}

    async def test_list_keys_excludes_system_files(self) -> None:
        store = AsyncInMemoryStore(run_id="test-run")
        # Save a regular artifact
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save("artifacts/findings", message)

        # Save a system file (simulating metadata)
        system_message = Message(
            id="msg-system",
            content={"status": "running"},
            schema=Schema("system_schema", "1.0.0"),
        )
        await store.save("_system/metadata", system_message)

        keys = await store.list_keys()

        assert "artifacts/findings" in keys
        assert "_system/metadata" not in keys


# =============================================================================
# Clear Tests (bulk removal)
# =============================================================================


class TestAsyncInMemoryStoreClear:
    """Tests for the clear() method."""

    async def test_clear_removes_all_artifacts(self) -> None:
        store = AsyncInMemoryStore(run_id="test-run")
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
