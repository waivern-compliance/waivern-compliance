"""Tests for DAGExecutor handling of PendingProcessingError (batch mode).

When a processor raises PendingProcessingError (e.g. via LLM batch API),
the executor should leave the artifact in not_started, continue executing
independent branches, and mark the run as interrupted.
"""

from pathlib import Path

from waivern_artifact_store import ArtifactStore
from waivern_core.errors import PendingProcessingError
from waivern_core.schemas import Schema

from waivern_orchestration.executor import DAGExecutor
from waivern_orchestration.models import ArtifactDefinition, SourceConfig
from waivern_orchestration.run_metadata import RunMetadata

from .test_executor_state import create_failing_connector_factory
from .test_helpers import (
    create_mock_connector_factory,
    create_mock_registry,
    create_simple_plan,
    create_test_message,
)

# =============================================================================
# Batch Handling Tests
# =============================================================================


class TestDAGExecutorBatchHandling:
    """Tests for PendingProcessingError handling in DAGExecutor."""

    async def test_pending_processing_error_leaves_artifact_not_started_and_run_interrupted(
        self,
    ) -> None:
        """PendingProcessingError leaves artifact in not_started, run marked interrupted."""
        # Arrange — single source artifact that raises PendingProcessingError
        output_schema = Schema("standard_input", "1.0.0")

        pending_factory = create_failing_connector_factory(
            "pending_source",
            [output_schema],
            PendingProcessingError("Batch pending for run-1"),
        )

        artifacts = {
            "data": ArtifactDefinition(
                source=SourceConfig(type="pending_source", properties={})
            ),
        }
        plan = create_simple_plan(artifacts, {"data": (None, output_schema)})

        registry = create_mock_registry(
            with_container=True,
            connector_factories={"pending_source": pending_factory},
        )
        executor = DAGExecutor(registry)

        # Act
        result = await executor.execute(plan)

        # Assert — artifact NOT in completed, failed, or skipped
        assert "data" not in result.completed
        assert "data" not in result.failed
        assert "data" not in result.skipped

        # Assert — run metadata status is "interrupted"
        store = registry.container.get_service(ArtifactStore)
        metadata = await RunMetadata.load(store, result.run_id)
        assert metadata.status == "interrupted"
        assert metadata.completed_at is not None

    async def test_dag_continues_independent_branches_after_pending_error(
        self,
    ) -> None:
        """Independent branches continue executing after a PendingProcessingError."""
        # Arrange — source_a (pending), source_b (succeeds), derived_c (depends on both)
        output_schema = Schema("standard_input", "1.0.0")
        message = create_test_message({"files": []})

        pending_factory = create_failing_connector_factory(
            "pending_source",
            [output_schema],
            PendingProcessingError("Batch pending"),
        )
        ok_factory = create_mock_connector_factory(
            "ok_source", [output_schema], message
        )

        artifacts = {
            "source_a": ArtifactDefinition(
                source=SourceConfig(type="pending_source", properties={})
            ),
            "source_b": ArtifactDefinition(
                source=SourceConfig(type="ok_source", properties={})
            ),
            "derived_c": ArtifactDefinition(inputs=["source_a", "source_b"]),
        }
        plan = create_simple_plan(
            artifacts,
            {
                "source_a": (None, output_schema),
                "source_b": (None, output_schema),
                "derived_c": (output_schema, output_schema),
            },
        )

        registry = create_mock_registry(
            with_container=True,
            connector_factories={
                "pending_source": pending_factory,
                "ok_source": ok_factory,
            },
        )
        executor = DAGExecutor(registry)

        # Act
        result = await executor.execute(plan)

        # Assert — source_b completed, source_a and derived_c did not
        assert "source_b" in result.completed
        assert "source_a" not in result.completed
        assert "source_a" not in result.failed
        assert "derived_c" not in result.completed

        # Assert — run interrupted (not failed)
        store = registry.container.get_service(ArtifactStore)
        metadata = await RunMetadata.load(store, result.run_id)
        assert metadata.status == "interrupted"

    async def test_multiple_artifacts_pending_in_same_gather_batch(self) -> None:
        """Multiple PendingProcessingErrors in the same gather batch are tracked."""
        # Arrange — two independent source artifacts, both pending
        output_schema = Schema("standard_input", "1.0.0")

        pending_factory = create_failing_connector_factory(
            "pending_source",
            [output_schema],
            PendingProcessingError("Batch pending"),
        )

        artifacts = {
            "source_a": ArtifactDefinition(
                source=SourceConfig(type="pending_source", properties={})
            ),
            "source_b": ArtifactDefinition(
                source=SourceConfig(type="pending_source", properties={})
            ),
        }
        plan = create_simple_plan(
            artifacts,
            {
                "source_a": (None, output_schema),
                "source_b": (None, output_schema),
            },
        )

        registry = create_mock_registry(
            with_container=True,
            connector_factories={"pending_source": pending_factory},
        )
        executor = DAGExecutor(registry)

        # Act
        result = await executor.execute(plan)

        # Assert — neither in completed or failed
        assert "source_a" not in result.completed
        assert "source_a" not in result.failed
        assert "source_b" not in result.completed
        assert "source_b" not in result.failed

        # Assert — run interrupted
        store = registry.container.get_service(ArtifactStore)
        metadata = await RunMetadata.load(store, result.run_id)
        assert metadata.status == "interrupted"

    async def test_resume_after_interrupted_run_completes_pending_artifacts(
        self, tmp_path: Path
    ) -> None:
        """Resuming an interrupted run re-executes pending artifacts successfully."""
        # Arrange — single source artifact, first run pending, second run succeeds
        output_schema = Schema("standard_input", "1.0.0")
        message = create_test_message({"files": []})

        pending_factory = create_failing_connector_factory(
            "my_source",
            [output_schema],
            PendingProcessingError("Batch pending"),
        )
        ok_factory = create_mock_connector_factory(
            "my_source", [output_schema], message
        )

        artifacts = {
            "data": ArtifactDefinition(
                source=SourceConfig(type="my_source", properties={})
            ),
        }
        plan = create_simple_plan(artifacts, {"data": (None, output_schema)})

        runbook_file = tmp_path / "runbook.yaml"
        runbook_file.write_text("name: test\ndescription: test\n")

        # First run — connector raises PendingProcessingError
        registry = create_mock_registry(
            with_container=True,
            connector_factories={"my_source": pending_factory},
        )
        executor = DAGExecutor(registry)

        result1 = await executor.execute(plan, runbook_path=runbook_file)
        assert "data" not in result1.completed

        store = registry.container.get_service(ArtifactStore)
        metadata = await RunMetadata.load(store, result1.run_id)
        assert metadata.status == "interrupted"

        # Second run (resume) — swap to a working connector
        registry.connector_factories["my_source"] = ok_factory

        result2 = await executor.execute(
            plan,
            runbook_path=runbook_file,
            resume_run_id=result1.run_id,
        )

        # Assert — artifact now completed
        assert "data" in result2.completed

        # Assert — status transitioned to completed
        metadata2 = await RunMetadata.load(store, result2.run_id)
        assert metadata2.status == "completed"

    async def test_mixed_pending_failed_and_succeeded_artifacts(self) -> None:
        """Pending, failed, and succeeded artifacts coexist with correct final status."""
        # Arrange — three independent source artifacts:
        #   source_ok (succeeds), source_pending (pending), source_fail (fails)
        output_schema = Schema("standard_input", "1.0.0")
        message = create_test_message({"files": []})

        ok_factory = create_mock_connector_factory(
            "ok_source", [output_schema], message
        )
        pending_factory = create_failing_connector_factory(
            "pending_source",
            [output_schema],
            PendingProcessingError("Batch pending"),
        )
        fail_factory = create_failing_connector_factory(
            "fail_source",
            [output_schema],
            RuntimeError("Connection failed"),
        )

        artifacts = {
            "source_ok": ArtifactDefinition(
                source=SourceConfig(type="ok_source", properties={})
            ),
            "source_pending": ArtifactDefinition(
                source=SourceConfig(type="pending_source", properties={})
            ),
            "source_fail": ArtifactDefinition(
                source=SourceConfig(type="fail_source", properties={})
            ),
        }
        plan = create_simple_plan(
            artifacts,
            {
                "source_ok": (None, output_schema),
                "source_pending": (None, output_schema),
                "source_fail": (None, output_schema),
            },
        )

        registry = create_mock_registry(
            with_container=True,
            connector_factories={
                "ok_source": ok_factory,
                "pending_source": pending_factory,
                "fail_source": fail_factory,
            },
        )
        executor = DAGExecutor(registry)

        # Act
        result = await executor.execute(plan)

        # Assert — each artifact in the correct bucket
        assert "source_ok" in result.completed
        assert "source_fail" in result.failed
        assert "source_pending" not in result.completed
        assert "source_pending" not in result.failed

        # Assert — interrupted takes priority over failed
        store = registry.container.get_service(ArtifactStore)
        metadata = await RunMetadata.load(store, result.run_id)
        assert metadata.status == "interrupted"
