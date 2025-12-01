"""Tests for InMemoryArtifactStore implementation."""

from __future__ import annotations

import threading
from unittest.mock import Mock

import pytest

from waivern_artifact_store.errors import ArtifactNotFoundError
from waivern_artifact_store.in_memory import InMemoryArtifactStore


class TestInMemoryArtifactStoreCRUD:
    """Test InMemoryArtifactStore CRUD operations."""

    def test_save_and_retrieve_artifact(self) -> None:
        """Test basic save and retrieve returns same Message reference."""
        store = InMemoryArtifactStore()
        message = Mock()  # Mock Message object
        step_id = "extract"

        store.save(step_id, message)
        retrieved = store.get(step_id)

        assert retrieved is message  # Same reference

    def test_exists_returns_correct_boolean(self) -> None:
        """Test exists() returns True for saved artifacts, False otherwise."""
        store = InMemoryArtifactStore()
        message = Mock()
        step_id = "extract"

        # Before save: should not exist
        assert not store.exists(step_id)

        # After save: should exist
        store.save(step_id, message)
        assert store.exists(step_id)

        # After clear: should not exist
        store.clear()
        assert not store.exists(step_id)

    def test_get_raises_error_for_missing_artifact(self) -> None:
        """Test get() raises ArtifactNotFoundError for missing artifact."""
        store = InMemoryArtifactStore()
        step_id = "nonexistent"

        with pytest.raises(ArtifactNotFoundError) as exc_info:
            store.get(step_id)

        # Verify error message includes step_id for debugging
        assert step_id in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()

    def test_clear_removes_all_artifacts(self) -> None:
        """Test clear() removes all stored artifacts."""
        store = InMemoryArtifactStore()

        # Save multiple artifacts
        store.save("step1", Mock())
        store.save("step2", Mock())
        store.save("step3", Mock())

        # Verify all exist
        assert store.exists("step1")
        assert store.exists("step2")
        assert store.exists("step3")

        # Clear all
        store.clear()

        # Verify none exist
        assert not store.exists("step1")
        assert not store.exists("step2")
        assert not store.exists("step3")

    def test_list_artifacts_returns_all_stored_ids(self) -> None:
        """Test list_artifacts() returns all stored artifact IDs."""
        store = InMemoryArtifactStore()

        # Empty store returns empty list
        assert store.list_artifacts() == []

        # Save artifacts
        store.save("artifact_a", Mock())
        store.save("artifact_b", Mock())
        store.save("artifact_c", Mock())

        # List should contain all IDs
        artifact_ids = store.list_artifacts()
        assert len(artifact_ids) == 3
        assert set(artifact_ids) == {"artifact_a", "artifact_b", "artifact_c"}

        # After clear, list should be empty again
        store.clear()
        assert store.list_artifacts() == []


class TestInMemoryArtifactStoreThreadSafety:
    """Test InMemoryArtifactStore thread safety."""

    def test_concurrent_operations_are_thread_safe(self) -> None:
        """Test multiple threads performing saves/gets concurrently without corruption."""
        store = InMemoryArtifactStore()
        num_threads = 10
        operations_per_thread = 100

        def worker(thread_id: int) -> None:
            """Worker function that saves and retrieves artifacts."""
            message = Mock()

            for i in range(operations_per_thread):
                step_id = f"thread_{thread_id}_op_{i}"
                store.save(step_id, message)
                retrieved = store.get(step_id)
                assert (
                    retrieved is message
                )  # Verify same object returned (no corruption)

        # Launch threads
        threads = [
            threading.Thread(target=worker, args=(i,)) for i in range(num_threads)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Verify all artifacts exist
        for thread_id in range(num_threads):
            for i in range(operations_per_thread):
                step_id = f"thread_{thread_id}_op_{i}"
                assert store.exists(step_id)
