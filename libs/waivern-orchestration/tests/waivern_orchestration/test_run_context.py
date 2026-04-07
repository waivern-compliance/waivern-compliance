"""Tests for RunContext model."""

from pathlib import Path

import pytest
from waivern_artifact_store.in_memory import AsyncInMemoryStore
from waivern_core.schemas import Schema

from waivern_orchestration.models import ArtifactDefinition, SourceConfig
from waivern_orchestration.planner import ExecutionPlan
from waivern_orchestration.run_context import RunContext

from .test_helpers import create_simple_plan

# =============================================================================
# Helpers
# =============================================================================


def _source_artifact() -> ArtifactDefinition:
    return ArtifactDefinition(source=SourceConfig(type="fs", properties={}))


def _two_artifact_plan() -> ExecutionPlan:
    """Plan with source 'a' and derived 'b'."""
    artifacts = {
        "a": _source_artifact(),
        "b": ArtifactDefinition(inputs="a"),
    }
    output = Schema("std", "1.0.0")
    schemas: dict[str, tuple[list[Schema] | None, Schema]] = {
        "a": (None, output),
        "b": ([output], output),
    }
    return create_simple_plan(artifacts, schemas)


# =============================================================================
# Creation Tests
# =============================================================================


class TestRunContextNew:
    """Tests for RunContext.new() factory method."""

    def test_new_creates_running_metadata(self, tmp_path: Path) -> None:
        runbook_file = tmp_path / "test.yaml"
        runbook_file.write_text("name: test")
        plan = _two_artifact_plan()
        ctx = RunContext.new(plan, runbook_path=runbook_file)

        assert ctx.metadata.status == "running"
        assert ctx.metadata.runbook_path == str(runbook_file)
        assert ctx.metadata.run_id  # non-empty

    def test_new_creates_state_with_all_artifacts_not_started(self) -> None:
        plan = _two_artifact_plan()
        ctx = RunContext.new(plan, runbook_path=None)

        assert ctx.state.run_id == ctx.metadata.run_id
        assert ctx.state.not_started == {"a", "b"}
        assert ctx.state.completed == set()

    def test_new_stores_plan_reference(self) -> None:
        plan = _two_artifact_plan()
        ctx = RunContext.new(plan, runbook_path=None)

        assert ctx.plan is plan

    def test_new_with_no_runbook_path(self) -> None:
        plan = _two_artifact_plan()
        ctx = RunContext.new(plan, runbook_path=None)

        assert ctx.metadata.status == "running"


# =============================================================================
# Persistence Tests
# =============================================================================


class TestRunContextPersistence:
    """Tests for save/load round-trip behaviour."""

    @pytest.fixture()
    def store(self) -> AsyncInMemoryStore:
        return AsyncInMemoryStore()

    async def test_save_all_then_load_round_trip(
        self, store: AsyncInMemoryStore
    ) -> None:
        plan = _two_artifact_plan()
        ctx = RunContext.new(plan, runbook_path=None)
        await ctx.save_all(store)

        restored = await RunContext.load(store, ctx.metadata.run_id)

        assert restored.metadata.run_id == ctx.metadata.run_id
        assert restored.metadata.status == "running"
        assert restored.state.not_started == {"a", "b"}
        assert restored.plan.runbook.name == plan.runbook.name
        assert set(restored.plan.runbook.artifacts.keys()) == {"a", "b"}

    async def test_save_metadata_persists_only_metadata(
        self, store: AsyncInMemoryStore
    ) -> None:
        plan = _two_artifact_plan()
        ctx = RunContext.new(plan, runbook_path=None)
        await ctx.save_all(store)

        # Mutate metadata and save only metadata
        ctx.metadata.mark_interrupted()
        await ctx.save_metadata(store)

        # Load and verify metadata changed but state unchanged
        restored = await RunContext.load(store, ctx.metadata.run_id)
        assert restored.metadata.status == "interrupted"
        assert restored.state.not_started == {"a", "b"}

    async def test_save_state_persists_only_state(
        self, store: AsyncInMemoryStore
    ) -> None:
        plan = _two_artifact_plan()
        ctx = RunContext.new(plan, runbook_path=None)
        await ctx.save_all(store)

        # Mutate state and save only state
        ctx.state.mark_completed("a")
        await ctx.save_state(store)

        # Load and verify state changed but metadata unchanged
        restored = await RunContext.load(store, ctx.metadata.run_id)
        assert restored.state.completed == {"a"}
        assert restored.state.not_started == {"b"}
        assert restored.metadata.status == "running"  # unchanged


# =============================================================================
# Validation Tests
# =============================================================================


class TestRunContextValidateResumable:
    """Tests for validate_resumable()."""

    def test_validate_resumable_allows_interrupted(self) -> None:
        plan = _two_artifact_plan()
        ctx = RunContext.new(plan, runbook_path=None)
        ctx.metadata.mark_interrupted()

        ctx.validate_resumable()  # should not raise

    def test_validate_resumable_allows_failed(self) -> None:
        plan = _two_artifact_plan()
        ctx = RunContext.new(plan, runbook_path=None)
        ctx.metadata.mark_failed()

        ctx.validate_resumable()  # should not raise

    def test_validate_resumable_rejects_running(self) -> None:
        plan = _two_artifact_plan()
        ctx = RunContext.new(plan, runbook_path=None)
        # status is "running" by default from new()

        with pytest.raises(ValueError, match="running"):
            ctx.validate_resumable()

    def test_validate_resumable_rejects_completed(self) -> None:
        plan = _two_artifact_plan()
        ctx = RunContext.new(plan, runbook_path=None)
        ctx.metadata.mark_completed()

        with pytest.raises(ValueError, match="completed"):
            ctx.validate_resumable()
