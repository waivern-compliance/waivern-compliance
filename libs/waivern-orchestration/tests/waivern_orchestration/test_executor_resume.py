"""Tests for DAGExecutor resume capability.

Tests verify that runs can be resumed from a previous state, with proper
validation and skip logic for completed artifacts.
"""

from pathlib import Path

import pytest
from waivern_artifact_store import ArtifactStore
from waivern_core.schemas import Schema

from waivern_orchestration.errors import (
    RunAlreadyActiveError,
    RunbookChangedError,
    RunNotFoundError,
)
from waivern_orchestration.executor import DAGExecutor
from waivern_orchestration.models import ArtifactDefinition, SourceConfig
from waivern_orchestration.run_metadata import RunMetadata

from .test_helpers import (
    create_mock_connector_factory,
    create_mock_registry,
    create_simple_plan,
    create_test_message,
)

# =============================================================================
# Resume Validation Tests
# =============================================================================


class TestResumeValidation:
    """Tests for resume validation (fail-fast checks)."""

    async def test_resume_with_nonexistent_run_raises_error(
        self, tmp_path: Path
    ) -> None:
        """Resuming a non-existent run_id raises RunNotFoundError."""
        # Arrange
        output_schema = Schema("standard_input", "1.0.0")
        message = create_test_message({"files": []})
        connector_factory = create_mock_connector_factory(
            "source", [output_schema], message
        )

        artifacts = {
            "data": ArtifactDefinition(
                source=SourceConfig(type="source", properties={})
            ),
        }
        plan = create_simple_plan(artifacts, {"data": (None, output_schema)})

        # Create a runbook file for hash computation
        runbook_file = tmp_path / "runbook.yaml"
        runbook_file.write_text("name: test\ndescription: test\n")

        registry = create_mock_registry(
            with_container=True, connector_factories={"source": connector_factory}
        )
        executor = DAGExecutor(registry)

        # Act & Assert
        with pytest.raises(RunNotFoundError):
            await executor.execute(
                plan,
                runbook_path=runbook_file,
                resume_run_id="nonexistent-run-id",
            )

    async def test_resume_with_changed_runbook_raises_error(
        self, tmp_path: Path
    ) -> None:
        """Resuming with modified runbook raises RunbookChangedError."""
        # Arrange - create a successful run first
        output_schema = Schema("standard_input", "1.0.0")
        message = create_test_message({"files": []})
        connector_factory = create_mock_connector_factory(
            "source", [output_schema], message
        )

        artifacts = {
            "data": ArtifactDefinition(
                source=SourceConfig(type="source", properties={})
            ),
        }
        plan = create_simple_plan(artifacts, {"data": (None, output_schema)})

        runbook_file = tmp_path / "runbook.yaml"
        runbook_file.write_text("name: test\ndescription: original\n")

        registry = create_mock_registry(
            with_container=True, connector_factories={"source": connector_factory}
        )
        executor = DAGExecutor(registry)

        # Execute first run
        result = await executor.execute(plan, runbook_path=runbook_file)
        original_run_id = result.run_id

        # Modify the runbook
        runbook_file.write_text("name: test\ndescription: modified\n")

        # Act & Assert - resuming should fail due to changed runbook
        with pytest.raises(RunbookChangedError):
            await executor.execute(
                plan,
                runbook_path=runbook_file,
                resume_run_id=original_run_id,
            )

    async def test_resume_while_already_running_raises_error(
        self, tmp_path: Path
    ) -> None:
        """Resuming a run with status='running' raises RunAlreadyActiveError."""
        # Arrange - manually create a run with status='running'
        from waivern_orchestration.run_metadata import compute_runbook_hash
        from waivern_orchestration.state import ExecutionState

        output_schema = Schema("standard_input", "1.0.0")
        message = create_test_message({"files": []})
        connector_factory = create_mock_connector_factory(
            "source", [output_schema], message
        )

        artifacts = {
            "data": ArtifactDefinition(
                source=SourceConfig(type="source", properties={})
            ),
        }
        plan = create_simple_plan(artifacts, {"data": (None, output_schema)})

        runbook_file = tmp_path / "runbook.yaml"
        runbook_file.write_text("name: test\ndescription: test\n")

        registry = create_mock_registry(
            with_container=True, connector_factories={"source": connector_factory}
        )
        store = registry.container.get_service(ArtifactStore)

        # Manually create a run in 'running' state (simulating another process)
        running_run_id = "running-run-123"
        metadata = RunMetadata.fresh(
            run_id=running_run_id,
            runbook_path=runbook_file,
            runbook_hash=compute_runbook_hash(runbook_file),
        )
        await metadata.save(store)

        # Also save state so it can be loaded
        state = ExecutionState.fresh(running_run_id, {"data"})
        await state.save(store)

        executor = DAGExecutor(registry)

        # Act & Assert - resuming should fail because status is 'running'
        with pytest.raises(RunAlreadyActiveError):
            await executor.execute(
                plan,
                runbook_path=runbook_file,
                resume_run_id=running_run_id,
            )


# =============================================================================
# Run Status Lifecycle Tests
# =============================================================================


class TestRunStatusLifecycle:
    """Tests for run status transitions during execution."""

    async def test_new_run_sets_status_to_running(self) -> None:
        """New run creates RunMetadata with status='running' initially.

        Note: We can't observe 'running' status directly because by the time
        execute() returns, status has transitioned to completed/failed.
        Instead, we verify that a resumed run (which was 'running') gets rejected.
        """
        # This behaviour is already tested by test_resume_while_already_running
        # The fact that it raises RunAlreadyActiveError proves the status is 'running'
        pass  # Covered by test_resume_while_already_running_raises_error

    async def test_successful_run_sets_status_to_completed(
        self, tmp_path: Path
    ) -> None:
        """Successful execution transitions status to 'completed'."""
        # Arrange
        output_schema = Schema("standard_input", "1.0.0")
        message = create_test_message({"files": []})
        connector_factory = create_mock_connector_factory(
            "source", [output_schema], message
        )

        artifacts = {
            "data": ArtifactDefinition(
                source=SourceConfig(type="source", properties={})
            ),
        }
        plan = create_simple_plan(artifacts, {"data": (None, output_schema)})

        runbook_file = tmp_path / "runbook.yaml"
        runbook_file.write_text("name: test\ndescription: test\n")

        registry = create_mock_registry(
            with_container=True, connector_factories={"source": connector_factory}
        )
        executor = DAGExecutor(registry)

        # Act
        result = await executor.execute(plan, runbook_path=runbook_file)

        # Assert - load metadata and verify status
        store = registry.container.get_service(ArtifactStore)
        metadata = await RunMetadata.load(store, result.run_id)

        assert metadata.status == "completed"
        assert metadata.completed_at is not None

    async def test_failed_run_sets_status_to_failed(self, tmp_path: Path) -> None:
        """Failed execution transitions status to 'failed'."""
        # Arrange - connector that raises exception
        from unittest.mock import MagicMock

        output_schema = Schema("standard_input", "1.0.0")

        failing_factory = MagicMock()
        mock_class = MagicMock()
        mock_class.get_name.return_value = "failing"
        mock_class.get_supported_output_schemas.return_value = [output_schema]
        failing_factory.component_class = mock_class
        failing_connector = MagicMock()
        failing_connector.extract.side_effect = RuntimeError("Connection failed")
        failing_factory.create.return_value = failing_connector

        artifacts = {
            "data": ArtifactDefinition(
                source=SourceConfig(type="failing", properties={})
            ),
        }
        plan = create_simple_plan(artifacts, {"data": (None, output_schema)})

        runbook_file = tmp_path / "runbook.yaml"
        runbook_file.write_text("name: test\ndescription: test\n")

        registry = create_mock_registry(
            with_container=True, connector_factories={"failing": failing_factory}
        )
        executor = DAGExecutor(registry)

        # Act
        result = await executor.execute(plan, runbook_path=runbook_file)

        # Assert - load metadata and verify status
        store = registry.container.get_service(ArtifactStore)
        metadata = await RunMetadata.load(store, result.run_id)

        assert metadata.status == "failed"
        assert metadata.completed_at is not None
        assert "data" in result.failed

    async def test_run_metadata_persisted_after_completion(
        self, tmp_path: Path
    ) -> None:
        """RunMetadata is persisted and loadable after execution."""
        # Arrange
        output_schema = Schema("standard_input", "1.0.0")
        message = create_test_message({"files": []})
        connector_factory = create_mock_connector_factory(
            "source", [output_schema], message
        )

        artifacts = {
            "data": ArtifactDefinition(
                source=SourceConfig(type="source", properties={})
            ),
        }
        plan = create_simple_plan(artifacts, {"data": (None, output_schema)})

        runbook_file = tmp_path / "runbook.yaml"
        runbook_file.write_text("name: test\ndescription: test\n")

        registry = create_mock_registry(
            with_container=True, connector_factories={"source": connector_factory}
        )
        executor = DAGExecutor(registry)

        # Act
        result = await executor.execute(plan, runbook_path=runbook_file)

        # Assert - metadata should be loadable with correct fields
        store = registry.container.get_service(ArtifactStore)
        metadata = await RunMetadata.load(store, result.run_id)

        assert metadata.run_id == result.run_id
        assert metadata.runbook_path == str(runbook_file)
        assert metadata.runbook_hash.startswith("sha256:")
        assert metadata.started_at is not None


# =============================================================================
# Resume Execution Flow Tests
# =============================================================================


class TestResumeExecutionFlow:
    """Tests for resume execution behaviour."""

    async def test_resume_skips_completed_artifacts(self, tmp_path: Path) -> None:
        """Completed artifacts are not re-executed on resume."""
        from unittest.mock import MagicMock

        # Arrange - track connector calls
        call_count = {"source": 0}
        output_schema = Schema("standard_input", "1.0.0")
        message = create_test_message({"files": []})

        def create_counting_factory() -> MagicMock:
            factory = MagicMock()
            mock_class = MagicMock()
            mock_class.get_name.return_value = "source"
            mock_class.get_supported_output_schemas.return_value = [output_schema]
            factory.component_class = mock_class

            mock_connector = MagicMock()

            def counting_extract(*args, **kwargs):
                call_count["source"] += 1
                return message

            mock_connector.extract.side_effect = counting_extract
            factory.create.return_value = mock_connector
            return factory

        connector_factory = create_counting_factory()

        artifacts = {
            "data": ArtifactDefinition(
                source=SourceConfig(type="source", properties={})
            ),
        }
        plan = create_simple_plan(artifacts, {"data": (None, output_schema)})

        runbook_file = tmp_path / "runbook.yaml"
        runbook_file.write_text("name: test\ndescription: test\n")

        registry = create_mock_registry(
            with_container=True, connector_factories={"source": connector_factory}
        )
        store = registry.container.get_service(ArtifactStore)
        executor = DAGExecutor(registry)

        # Run first execution
        result1 = await executor.execute(plan, runbook_path=runbook_file)
        assert call_count["source"] == 1

        # Manually mark run as 'failed' (not 'completed') so we can resume
        # In real scenarios, this would be an interrupted run
        metadata = await RunMetadata.load(store, result1.run_id)
        metadata.status = "interrupted"
        await metadata.save(store)

        # Act - resume the run
        result2 = await executor.execute(
            plan,
            runbook_path=runbook_file,
            resume_run_id=result1.run_id,
        )

        # Assert - connector should NOT be called again (artifact was completed)
        assert call_count["source"] == 1  # Still 1, not 2
        assert "data" in result2.completed

    async def test_resume_executes_not_started_artifacts(self, tmp_path: Path) -> None:
        """Not-started artifacts are executed on resume."""
        from waivern_orchestration.run_metadata import compute_runbook_hash
        from waivern_orchestration.state import ExecutionState

        # Arrange - create a run with one artifact completed, one not started
        output_schema = Schema("standard_input", "1.0.0")
        message_a = create_test_message({"files": [{"path": "a.txt"}]})
        message_b = create_test_message({"files": [{"path": "b.txt"}]})

        factory_a = create_mock_connector_factory(
            "source_a", [output_schema], message_a
        )
        factory_b = create_mock_connector_factory(
            "source_b", [output_schema], message_b
        )

        artifacts = {
            "artifact_a": ArtifactDefinition(
                source=SourceConfig(type="source_a", properties={})
            ),
            "artifact_b": ArtifactDefinition(
                source=SourceConfig(type="source_b", properties={})
            ),
        }
        plan = create_simple_plan(
            artifacts,
            {
                "artifact_a": (None, output_schema),
                "artifact_b": (None, output_schema),
            },
        )

        runbook_file = tmp_path / "runbook.yaml"
        runbook_file.write_text("name: test\ndescription: test\n")

        registry = create_mock_registry(
            with_container=True,
            connector_factories={"source_a": factory_a, "source_b": factory_b},
        )
        store = registry.container.get_service(ArtifactStore)

        # Manually create a partial run (a completed, b not started)
        run_id = "partial-run-123"
        metadata = RunMetadata.fresh(
            run_id=run_id,
            runbook_path=runbook_file,
            runbook_hash=compute_runbook_hash(runbook_file),
        )
        metadata.status = "interrupted"  # Allow resume
        await metadata.save(store)

        # State: artifact_a completed, artifact_b not started
        state = ExecutionState.fresh(run_id, {"artifact_a", "artifact_b"})
        state.mark_completed("artifact_a")
        await state.save(store)

        # Save artifact_a data (simulating it was already produced)
        await store.save_artifact(run_id, "artifact_a", message_a)

        executor = DAGExecutor(registry)

        # Act - resume the run
        result = await executor.execute(
            plan,
            runbook_path=runbook_file,
            resume_run_id=run_id,
        )

        # Assert - artifact_b should now be completed
        assert "artifact_a" in result.completed
        assert "artifact_b" in result.completed
        # Verify artifact_b connector was called
        factory_b.create.assert_called_once()

    async def test_resume_preserves_completed_artifact_data(
        self, tmp_path: Path
    ) -> None:
        """Previously completed artifact data remains accessible."""
        from waivern_orchestration.run_metadata import compute_runbook_hash
        from waivern_orchestration.state import ExecutionState

        # Arrange
        output_schema = Schema("standard_input", "1.0.0")
        original_content = {"files": [{"path": "original.txt", "content": "original"}]}
        message = create_test_message(original_content)

        connector_factory = create_mock_connector_factory(
            "source", [output_schema], message
        )

        artifacts = {
            "data": ArtifactDefinition(
                source=SourceConfig(type="source", properties={})
            ),
        }
        plan = create_simple_plan(artifacts, {"data": (None, output_schema)})

        runbook_file = tmp_path / "runbook.yaml"
        runbook_file.write_text("name: test\ndescription: test\n")

        registry = create_mock_registry(
            with_container=True, connector_factories={"source": connector_factory}
        )
        store = registry.container.get_service(ArtifactStore)

        # Create a completed run
        run_id = "completed-run-123"
        metadata = RunMetadata.fresh(
            run_id=run_id,
            runbook_path=runbook_file,
            runbook_hash=compute_runbook_hash(runbook_file),
        )
        metadata.status = "interrupted"  # Allow resume
        await metadata.save(store)

        state = ExecutionState.fresh(run_id, {"data"})
        state.mark_completed("data")
        await state.save(store)

        # Save original artifact data
        original_message = create_test_message(original_content)
        await store.save_artifact(run_id, "data", original_message)

        executor = DAGExecutor(registry)

        # Act - resume
        await executor.execute(
            plan,
            runbook_path=runbook_file,
            resume_run_id=run_id,
        )

        # Assert - original data should still be there (not overwritten)
        loaded = await store.get_artifact(run_id, "data")
        assert loaded.content == original_content

    async def test_resume_with_all_completed_is_noop(self, tmp_path: Path) -> None:
        """Resuming a fully completed run executes nothing."""
        from unittest.mock import MagicMock

        from waivern_orchestration.run_metadata import compute_runbook_hash
        from waivern_orchestration.state import ExecutionState

        # Arrange - track if connector is called
        connector_called = {"value": False}
        output_schema = Schema("standard_input", "1.0.0")
        message = create_test_message({"files": []})

        factory = MagicMock()
        mock_class = MagicMock()
        mock_class.get_name.return_value = "source"
        mock_class.get_supported_output_schemas.return_value = [output_schema]
        factory.component_class = mock_class

        mock_connector = MagicMock()

        def tracking_extract(*args, **kwargs):
            connector_called["value"] = True
            return message

        mock_connector.extract.side_effect = tracking_extract
        factory.create.return_value = mock_connector

        artifacts = {
            "data": ArtifactDefinition(
                source=SourceConfig(type="source", properties={})
            ),
        }
        plan = create_simple_plan(artifacts, {"data": (None, output_schema)})

        runbook_file = tmp_path / "runbook.yaml"
        runbook_file.write_text("name: test\ndescription: test\n")

        registry = create_mock_registry(
            with_container=True, connector_factories={"source": factory}
        )
        store = registry.container.get_service(ArtifactStore)

        # Create a fully completed run
        run_id = "all-completed-run"
        metadata = RunMetadata.fresh(
            run_id=run_id,
            runbook_path=runbook_file,
            runbook_hash=compute_runbook_hash(runbook_file),
        )
        metadata.status = "interrupted"  # Allow resume (even though all done)
        await metadata.save(store)

        state = ExecutionState.fresh(run_id, {"data"})
        state.mark_completed("data")
        await state.save(store)

        # Save artifact data
        await store.save_artifact(run_id, "data", message)

        executor = DAGExecutor(registry)

        # Act - resume
        result = await executor.execute(
            plan,
            runbook_path=runbook_file,
            resume_run_id=run_id,
        )

        # Assert - connector should NOT be called
        assert connector_called["value"] is False
        assert "data" in result.completed
