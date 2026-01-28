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
        store = AsyncInMemoryStore()
        message = Message(
            id="msg-1",
            content={"data": "test-value"},
            schema=Schema("test_schema", "1.0.0"),
        )

        await store.save("test-run", "my_artifact", message)

        retrieved = await store.get("test-run", "my_artifact")
        assert retrieved.id == "msg-1"
        assert retrieved.content == {"data": "test-value"}

    async def test_save_overwrites_existing_artifact(self) -> None:
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

        await store.save("test-run", "artifact", original)
        await store.save("test-run", "artifact", updated)

        retrieved = await store.get("test-run", "artifact")
        assert retrieved.id == "msg-2"
        assert retrieved.content == {"version": "updated"}


# =============================================================================
# Get Tests (retrieval and error handling)
# =============================================================================


class TestAsyncInMemoryStoreGet:
    """Tests for the get() method."""

    async def test_get_raises_artifact_not_found_for_missing_key(self) -> None:
        store = AsyncInMemoryStore()

        with pytest.raises(ArtifactNotFoundError):
            await store.get("test-run", "nonexistent")


# =============================================================================
# Exists Tests (presence checking)
# =============================================================================


class TestAsyncInMemoryStoreExists:
    """Tests for the exists() method."""

    async def test_exists_returns_true_after_save(self) -> None:
        store = AsyncInMemoryStore()
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save("test-run", "artifact", message)

        result = await store.exists("test-run", "artifact")

        assert result is True

    async def test_exists_returns_false_for_unsaved_key(self) -> None:
        store = AsyncInMemoryStore()

        result = await store.exists("test-run", "nonexistent")

        assert result is False


# =============================================================================
# Delete Tests (removal and idempotency)
# =============================================================================


class TestAsyncInMemoryStoreDelete:
    """Tests for the delete() method."""

    async def test_delete_removes_saved_artifact(self) -> None:
        store = AsyncInMemoryStore()
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save("test-run", "artifact", message)
        assert await store.exists("test-run", "artifact")

        await store.delete("test-run", "artifact")

        assert not await store.exists("test-run", "artifact")

    async def test_delete_does_not_raise_for_missing_key(self) -> None:
        store = AsyncInMemoryStore()

        # Should not raise any exception
        await store.delete("test-run", "nonexistent")


# =============================================================================
# List Keys Tests (enumeration and filtering)
# =============================================================================


class TestAsyncInMemoryStoreListKeys:
    """Tests for the list_keys() method."""

    async def test_list_keys_returns_all_saved_keys(self) -> None:
        store = AsyncInMemoryStore()
        for key in ["alpha", "beta", "gamma"]:
            message = Message(
                id=f"msg-{key}",
                content={"key": key},
                schema=Schema("test_schema", "1.0.0"),
            )
            await store.save("test-run", key, message)

        keys = await store.list_keys("test-run")

        assert set(keys) == {"alpha", "beta", "gamma"}

    async def test_list_keys_with_prefix_filters_results(self) -> None:
        store = AsyncInMemoryStore()
        for key in ["artifacts/a", "artifacts/b", "cache/x"]:
            message = Message(
                id=f"msg-{key}",
                content={"key": key},
                schema=Schema("test_schema", "1.0.0"),
            )
            await store.save("test-run", key, message)

        keys = await store.list_keys("test-run", prefix="artifacts")

        assert set(keys) == {"artifacts/a", "artifacts/b"}

    async def test_list_keys_excludes_system_files(self) -> None:
        store = AsyncInMemoryStore()
        # Save a regular artifact
        message = Message(
            id="msg-1",
            content={"data": "value"},
            schema=Schema("test_schema", "1.0.0"),
        )
        await store.save("test-run", "artifacts/findings", message)

        # Save a system file (simulating metadata)
        system_message = Message(
            id="msg-system",
            content={"status": "running"},
            schema=Schema("system_schema", "1.0.0"),
        )
        await store.save("test-run", "_system/metadata", system_message)

        keys = await store.list_keys("test-run")

        assert "artifacts/findings" in keys
        assert "_system/metadata" not in keys


# =============================================================================
# Clear Tests (bulk removal)
# =============================================================================


class TestAsyncInMemoryStoreClear:
    """Tests for the clear() method."""

    async def test_clear_removes_all_artifacts(self) -> None:
        store = AsyncInMemoryStore()
        for key in ["alpha", "beta", "nested/gamma"]:
            message = Message(
                id=f"msg-{key}",
                content={"key": key},
                schema=Schema("test_schema", "1.0.0"),
            )
            await store.save("test-run", key, message)
        assert len(await store.list_keys("test-run")) == 3

        await store.clear("test-run")

        assert await store.list_keys("test-run") == []


# =============================================================================
# Run Isolation Tests (singleton store, multiple runs)
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

        await store.save("run-1", "artifact", message_run1)
        await store.save("run-2", "artifact", message_run2)

        retrieved_run1 = await store.get("run-1", "artifact")
        retrieved_run2 = await store.get("run-2", "artifact")

        assert retrieved_run1.content == {"run": "1"}
        assert retrieved_run2.content == {"run": "2"}

    async def test_clear_only_affects_specified_run(self) -> None:
        store = AsyncInMemoryStore()
        for run_id in ["run-1", "run-2"]:
            message = Message(
                id=f"msg-{run_id}",
                content={"run": run_id},
                schema=Schema("test_schema", "1.0.0"),
            )
            await store.save(run_id, "artifact", message)

        await store.clear("run-1")

        assert not await store.exists("run-1", "artifact")
        assert await store.exists("run-2", "artifact")
