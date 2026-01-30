"""Tests for DAGExecutor state persistence.

Tests verify that ExecutionState is properly tracked and persisted during
DAG execution, enabling resume capability.
"""

import asyncio
from unittest.mock import MagicMock

from waivern_artifact_store import ArtifactStore
from waivern_core.schemas import Schema

from waivern_orchestration.executor import DAGExecutor
from waivern_orchestration.models import ArtifactDefinition, SourceConfig
from waivern_orchestration.state import ExecutionState

from .test_helpers import (
    create_mock_connector_factory,
    create_mock_registry,
    create_simple_plan,
    create_test_message,
)


def create_failing_connector_factory(
    name: str,
    output_schemas: list[Schema],
    exception: BaseException,
) -> MagicMock:
    """Create a mock connector factory that raises an exception on extract."""
    factory = MagicMock()
    mock_class = MagicMock()
    mock_class.get_name.return_value = name
    mock_class.get_supported_output_schemas.return_value = output_schemas
    factory.component_class = mock_class

    mock_connector = MagicMock()
    mock_connector.extract.side_effect = exception
    factory.create.return_value = mock_connector

    return factory


# =============================================================================
# State Initialisation Tests
# =============================================================================


class TestDAGExecutorStateInitialisation:
    """Tests for ExecutionState initialisation at execution start."""

    def test_fresh_state_created_with_all_artifact_ids(self) -> None:
        """State is initialised with all artifacts in not_started.

        We verify this indirectly: after successful execution, all artifacts
        should have transitioned from not_started to completed, proving they
        were tracked from the start.
        """
        # Arrange - three independent source artifacts
        output_schema = Schema("standard_input", "1.0.0")
        message = create_test_message({"files": []})

        connector_factory = create_mock_connector_factory(
            "source", [output_schema], message
        )

        artifacts = {
            "artifact_a": ArtifactDefinition(
                source=SourceConfig(type="source", properties={})
            ),
            "artifact_b": ArtifactDefinition(
                source=SourceConfig(type="source", properties={})
            ),
            "artifact_c": ArtifactDefinition(
                source=SourceConfig(type="source", properties={})
            ),
        }
        plan = create_simple_plan(
            artifacts,
            {
                "artifact_a": (None, output_schema),
                "artifact_b": (None, output_schema),
                "artifact_c": (None, output_schema),
            },
        )

        registry = create_mock_registry(
            with_container=True, connector_factories={"source": connector_factory}
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert - load state and verify all artifacts were tracked
        store = registry.container.get_service(ArtifactStore)
        state = asyncio.run(ExecutionState.load(store, result.run_id))

        # All three artifacts should be in completed (successful execution)
        assert state.completed == {"artifact_a", "artifact_b", "artifact_c"}
        # Nothing should remain in not_started
        assert state.not_started == set()


# =============================================================================
# State Transition Tests
# =============================================================================


class TestDAGExecutorStateTransitions:
    """Tests for state transitions during execution."""

    def test_successful_artifact_marked_completed_in_state(self) -> None:
        """After connector succeeds, artifact moves to completed."""
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

        registry = create_mock_registry(
            with_container=True, connector_factories={"source": connector_factory}
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert
        store = registry.container.get_service(ArtifactStore)
        state = asyncio.run(ExecutionState.load(store, result.run_id))

        assert "data" in state.completed
        assert "data" not in state.failed
        assert "data" not in state.skipped

    def test_failed_artifact_marked_failed_in_state(self) -> None:
        """After connector fails, artifact moves to failed."""
        # Arrange - connector that raises exception
        output_schema = Schema("standard_input", "1.0.0")

        failing_factory = create_failing_connector_factory(
            "failing", [output_schema], RuntimeError("Connection failed")
        )

        artifacts = {
            "data": ArtifactDefinition(
                source=SourceConfig(type="failing", properties={})
            ),
        }
        plan = create_simple_plan(artifacts, {"data": (None, output_schema)})

        registry = create_mock_registry(
            with_container=True, connector_factories={"failing": failing_factory}
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert
        store = registry.container.get_service(ArtifactStore)
        state = asyncio.run(ExecutionState.load(store, result.run_id))

        assert "data" in state.failed
        assert "data" not in state.completed

    def test_dependent_artifacts_marked_skipped_in_state(self) -> None:
        """When upstream fails, dependents move to skipped."""
        # Arrange - source fails, dependent should be skipped
        output_schema = Schema("standard_input", "1.0.0")

        failing_factory = create_failing_connector_factory(
            "failing", [output_schema], RuntimeError("Connection failed")
        )

        artifacts = {
            "source": ArtifactDefinition(
                source=SourceConfig(type="failing", properties={})
            ),
            "dependent": ArtifactDefinition(inputs="source"),
        }
        plan = create_simple_plan(
            artifacts,
            {
                "source": (None, output_schema),
                "dependent": (output_schema, output_schema),
            },
        )

        registry = create_mock_registry(
            with_container=True, connector_factories={"failing": failing_factory}
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert
        store = registry.container.get_service(ArtifactStore)
        state = asyncio.run(ExecutionState.load(store, result.run_id))

        assert "source" in state.failed
        assert "dependent" in state.skipped
        assert "dependent" not in state.failed


# =============================================================================
# State Persistence Tests
# =============================================================================


class TestDAGExecutorStatePersistence:
    """Tests for state persistence to ArtifactStore."""

    def test_state_persisted_after_each_artifact_completion(self) -> None:
        """State is saved to store after each artifact completes.

        We verify persistence by loading the state after execution completes.
        """
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

        registry = create_mock_registry(
            with_container=True, connector_factories={"source": connector_factory}
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert - state is persisted and loadable
        store = registry.container.get_service(ArtifactStore)
        state = asyncio.run(ExecutionState.load(store, result.run_id))

        assert state.completed == {"data"}

    def test_state_persisted_after_artifact_failure(self) -> None:
        """State is saved when artifact fails."""
        # Arrange
        output_schema = Schema("standard_input", "1.0.0")

        failing_factory = create_failing_connector_factory(
            "failing", [output_schema], RuntimeError("Connection failed")
        )

        artifacts = {
            "data": ArtifactDefinition(
                source=SourceConfig(type="failing", properties={})
            ),
        }
        plan = create_simple_plan(artifacts, {"data": (None, output_schema)})

        registry = create_mock_registry(
            with_container=True, connector_factories={"failing": failing_factory}
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert - failure state is persisted
        store = registry.container.get_service(ArtifactStore)
        state = asyncio.run(ExecutionState.load(store, result.run_id))

        assert state.failed == {"data"}

    def test_state_persisted_after_skipping_dependents(self) -> None:
        """State is saved after marking dependents as skipped."""
        # Arrange - chain of 3, first one fails
        output_schema = Schema("standard_input", "1.0.0")

        failing_factory = create_failing_connector_factory(
            "failing", [output_schema], RuntimeError("Connection failed")
        )

        artifacts = {
            "source": ArtifactDefinition(
                source=SourceConfig(type="failing", properties={})
            ),
            "middle": ArtifactDefinition(inputs="source"),
            "final": ArtifactDefinition(inputs="middle"),
        }
        plan = create_simple_plan(
            artifacts,
            {
                "source": (None, output_schema),
                "middle": (output_schema, output_schema),
                "final": (output_schema, output_schema),
            },
        )

        registry = create_mock_registry(
            with_container=True, connector_factories={"failing": failing_factory}
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert - skipped state is persisted
        store = registry.container.get_service(ArtifactStore)
        state = asyncio.run(ExecutionState.load(store, result.run_id))

        assert state.failed == {"source"}
        assert state.skipped == {"middle", "final"}

    def test_state_retrievable_from_store_after_execution(self) -> None:
        """Can load ExecutionState from store using run_id."""
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

        registry = create_mock_registry(
            with_container=True, connector_factories={"source": connector_factory}
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert - state can be loaded using the run_id from result
        store = registry.container.get_service(ArtifactStore)
        state = asyncio.run(ExecutionState.load(store, result.run_id))

        # Verify it's a valid ExecutionState with expected data
        assert isinstance(state, ExecutionState)
        assert state.completed == {"data"}
        assert state.not_started == set()
        assert state.last_checkpoint is not None


# =============================================================================
# State Consistency Tests
# =============================================================================


class TestDAGExecutorStateConsistency:
    """Tests for state consistency invariants."""

    def test_final_state_accounts_for_all_artifacts(self) -> None:
        """completed ∪ failed ∪ skipped = all artifacts.

        Tests with a mixed scenario: some succeed, one fails, some skipped.
        """
        # Arrange - parallel branches, one fails
        output_schema = Schema("standard_input", "1.0.0")
        message = create_test_message({"files": []})

        success_factory = create_mock_connector_factory(
            "success", [output_schema], message
        )
        failing_factory = create_failing_connector_factory(
            "failing", [output_schema], RuntimeError("Connection failed")
        )

        artifacts = {
            # Branch 1: succeeds
            "success_source": ArtifactDefinition(
                source=SourceConfig(type="success", properties={})
            ),
            "success_derived": ArtifactDefinition(inputs="success_source"),
            # Branch 2: fails, dependent skipped
            "failing_source": ArtifactDefinition(
                source=SourceConfig(type="failing", properties={})
            ),
            "skipped_derived": ArtifactDefinition(inputs="failing_source"),
        }
        plan = create_simple_plan(
            artifacts,
            {
                "success_source": (None, output_schema),
                "success_derived": (output_schema, output_schema),
                "failing_source": (None, output_schema),
                "skipped_derived": (output_schema, output_schema),
            },
        )

        registry = create_mock_registry(
            with_container=True,
            connector_factories={
                "success": success_factory,
                "failing": failing_factory,
            },
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert - all artifacts accounted for
        store = registry.container.get_service(ArtifactStore)
        state = asyncio.run(ExecutionState.load(store, result.run_id))

        all_artifacts = {
            "success_source",
            "success_derived",
            "failing_source",
            "skipped_derived",
        }
        accounted_for = state.completed | state.failed | state.skipped

        assert accounted_for == all_artifacts
        assert state.not_started == set()

        # Verify each category
        assert "success_source" in state.completed
        assert "success_derived" in state.completed
        assert "failing_source" in state.failed
        assert "skipped_derived" in state.skipped

    def test_execution_result_skipped_matches_state_skipped(self) -> None:
        """ExecutionResult.skipped matches state.skipped."""
        # Arrange - source fails, dependent skipped
        output_schema = Schema("standard_input", "1.0.0")

        failing_factory = create_failing_connector_factory(
            "failing", [output_schema], RuntimeError("Connection failed")
        )

        artifacts = {
            "source": ArtifactDefinition(
                source=SourceConfig(type="failing", properties={})
            ),
            "dependent": ArtifactDefinition(inputs="source"),
        }
        plan = create_simple_plan(
            artifacts,
            {
                "source": (None, output_schema),
                "dependent": (output_schema, output_schema),
            },
        )

        registry = create_mock_registry(
            with_container=True, connector_factories={"failing": failing_factory}
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert - result.skipped matches state.skipped
        store = registry.container.get_service(ArtifactStore)
        state = asyncio.run(ExecutionState.load(store, result.run_id))

        assert result.skipped == state.skipped
        assert result.skipped == {"dependent"}
