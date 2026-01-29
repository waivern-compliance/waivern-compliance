"""Tests for ExecutionState model."""

from datetime import UTC, datetime

import pytest
from waivern_artifact_store.errors import ArtifactNotFoundError
from waivern_artifact_store.in_memory import AsyncInMemoryStore

from waivern_orchestration.state import ExecutionState

# =============================================================================
# Factory Method Tests (fresh)
# =============================================================================


class TestExecutionStateFresh:
    """Tests for the fresh() factory method."""

    def test_fresh_creates_state_with_all_artifacts_in_not_started(self) -> None:
        artifact_ids = {"source_data", "findings", "validated_findings"}

        state = ExecutionState.fresh(artifact_ids)

        assert state.not_started == {"source_data", "findings", "validated_findings"}
        assert state.completed == set()
        assert state.failed == set()
        assert state.skipped == set()

    def test_fresh_sets_checkpoint_to_current_utc_time(self) -> None:
        before = datetime.now(UTC)

        state = ExecutionState.fresh({"artifact_a"})

        after = datetime.now(UTC)
        assert before <= state.last_checkpoint <= after


# =============================================================================
# State Transition Tests (mark_completed, mark_failed, mark_skipped)
# =============================================================================


class TestExecutionStateMarkCompleted:
    """Tests for the mark_completed() method."""

    def test_mark_completed_moves_artifact_from_not_started_to_completed(self) -> None:
        state = ExecutionState.fresh({"artifact_a", "artifact_b"})

        state.mark_completed("artifact_a")

        assert "artifact_a" in state.completed
        assert "artifact_a" not in state.not_started
        assert "artifact_b" in state.not_started

    def test_mark_completed_updates_last_checkpoint(self) -> None:
        state = ExecutionState.fresh({"artifact_a"})
        original_checkpoint = state.last_checkpoint

        # Small delay to ensure checkpoint changes
        state.mark_completed("artifact_a")

        assert state.last_checkpoint >= original_checkpoint

    def test_mark_completed_is_idempotent_for_already_completed_artifact(self) -> None:
        state = ExecutionState.fresh({"artifact_a", "artifact_b"})
        state.mark_completed("artifact_a")

        # Second call should be no-op (doesn't pollute or error)
        state.mark_completed("artifact_a")

        assert state.completed == {"artifact_a"}
        assert state.not_started == {"artifact_b"}

    def test_mark_completed_ignores_unknown_artifact(self) -> None:
        state = ExecutionState.fresh({"artifact_a"})

        # Should be no-op - doesn't pollute completed with unknown artifacts
        state.mark_completed("nonexistent_artifact")

        assert "nonexistent_artifact" not in state.completed
        assert state.not_started == {"artifact_a"}


class TestExecutionStateMarkFailed:
    """Tests for the mark_failed() method."""

    def test_mark_failed_moves_artifact_from_not_started_to_failed(self) -> None:
        state = ExecutionState.fresh({"artifact_a", "artifact_b"})

        state.mark_failed("artifact_a")

        assert "artifact_a" in state.failed
        assert "artifact_a" not in state.not_started
        assert "artifact_b" in state.not_started

    def test_mark_failed_updates_last_checkpoint(self) -> None:
        state = ExecutionState.fresh({"artifact_a"})
        original_checkpoint = state.last_checkpoint

        state.mark_failed("artifact_a")

        assert state.last_checkpoint >= original_checkpoint


class TestExecutionStateMarkSkipped:
    """Tests for the mark_skipped() method."""

    def test_mark_skipped_moves_multiple_artifacts_to_skipped(self) -> None:
        state = ExecutionState.fresh({"a", "b", "c", "d"})

        state.mark_skipped({"b", "c"})

        assert state.skipped == {"b", "c"}
        assert state.not_started == {"a", "d"}

    def test_mark_skipped_updates_last_checkpoint(self) -> None:
        state = ExecutionState.fresh({"artifact_a", "artifact_b"})
        original_checkpoint = state.last_checkpoint

        state.mark_skipped({"artifact_a"})

        assert state.last_checkpoint >= original_checkpoint


# =============================================================================
# Persistence Tests (save, load)
# =============================================================================


class TestExecutionStatePersistence:
    """Tests for save() and load() methods."""

    async def test_save_then_load_round_trip_preserves_state(self) -> None:
        store = AsyncInMemoryStore()
        run_id = "test-run-123"

        # Create state with mixed statuses
        original = ExecutionState.fresh({"a", "b", "c", "d"})
        original.mark_completed("a")
        original.mark_failed("b")
        original.mark_skipped({"c"})
        # "d" remains in not_started

        await original.save(store, run_id)
        loaded = await ExecutionState.load(store, run_id)

        assert loaded.completed == {"a"}
        assert loaded.failed == {"b"}
        assert loaded.skipped == {"c"}
        assert loaded.not_started == {"d"}

    async def test_load_raises_artifact_not_found_for_missing_state(self) -> None:
        store = AsyncInMemoryStore()

        with pytest.raises(ArtifactNotFoundError):
            await ExecutionState.load(store, "nonexistent-run")

    async def test_save_updates_last_checkpoint_before_persisting(self) -> None:
        store = AsyncInMemoryStore()
        run_id = "test-run-456"

        state = ExecutionState.fresh({"artifact_a"})
        original_checkpoint = state.last_checkpoint

        # Small delay to ensure time difference
        await state.save(store, run_id)

        # Reload and check checkpoint was updated
        loaded = await ExecutionState.load(store, run_id)
        assert loaded.last_checkpoint >= original_checkpoint
