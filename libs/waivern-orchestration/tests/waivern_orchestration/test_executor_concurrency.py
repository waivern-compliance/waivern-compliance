"""Tests for DAGExecutor concurrency, observability, and timeout behaviour."""

import asyncio
import threading
import time
from typing import Any
from unittest.mock import MagicMock

from waivern_artifact_store.base import ArtifactStore
from waivern_artifact_store.in_memory import AsyncInMemoryStore
from waivern_core.schemas import Schema
from waivern_core.services import ComponentRegistry, ServiceContainer, ServiceDescriptor

from waivern_orchestration.executor import DAGExecutor
from waivern_orchestration.models import (
    ArtifactDefinition,
    RunbookConfig,
    SourceConfig,
)

from .test_helpers import (
    create_mock_connector_factory,
    create_mock_registry,
    create_simple_plan,
    create_test_message,
)

# =============================================================================
# Concurrency Control
# =============================================================================


class TestDAGExecutorConcurrency:
    """Tests for concurrency control in DAGExecutor."""

    def test_concurrency_limit_respected(self) -> None:
        """At most max_concurrency artifacts execute simultaneously."""
        # Track concurrent execution count
        current_concurrent = 0
        max_concurrent_observed = 0
        lock = threading.Lock()

        output_schema = Schema("standard_input", "1.0.0")
        message = create_test_message({"files": []})

        def tracking_extract(*args: Any, **kwargs: Any) -> Any:
            """Extract that tracks concurrent execution count."""
            nonlocal current_concurrent, max_concurrent_observed

            with lock:
                current_concurrent += 1
                max_concurrent_observed = max(
                    max_concurrent_observed, current_concurrent
                )

            # Small delay to allow overlap detection
            time.sleep(0.01)

            with lock:
                current_concurrent -= 1

            return message

        # Create factory with tracking extract
        connector_factory = MagicMock()
        mock_class = MagicMock()
        mock_class.get_name.return_value = "source"
        mock_class.get_supported_output_schemas.return_value = [output_schema]
        connector_factory.component_class = mock_class
        mock_connector = MagicMock()
        mock_connector.extract.side_effect = tracking_extract
        connector_factory.create.return_value = mock_connector

        # Create 5 independent artifacts with max_concurrency=2
        artifacts = {
            f"data_{i}": ArtifactDefinition(
                source=SourceConfig(type="source", properties={})
            )
            for i in range(5)
        }
        artifact_schemas: dict[str, tuple[Schema | None, Schema]] = {
            f"data_{i}": (None, output_schema) for i in range(5)
        }
        plan = create_simple_plan(
            artifacts,
            artifact_schemas,
            runbook_config=RunbookConfig(max_concurrency=2),
        )

        registry = create_mock_registry(
            with_container=True, connector_factories={"source": connector_factory}
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert - all completed and concurrency was limited
        assert len(result.completed) == 5
        assert len(result.failed) == 0
        assert max_concurrent_observed <= 2, (
            f"Expected max 2 concurrent, but observed {max_concurrent_observed}"
        )


# =============================================================================
# Observability
# =============================================================================


class TestDAGExecutorObservability:
    """Tests for observability features in DAGExecutor."""

    def test_list_artifacts_after_execution(self) -> None:
        """After execution, store.list_keys() returns all produced IDs for the run."""
        # Arrange - use singleton store so we can access it after execution

        store = AsyncInMemoryStore()
        container = ServiceContainer()
        # Create a factory that returns our pre-created instance
        store_factory = MagicMock()
        store_factory.create.return_value = store
        container.register(ServiceDescriptor(ArtifactStore, store_factory, "singleton"))

        output_schema = Schema("standard_input", "1.0.0")
        message = create_test_message({"files": []})
        connector_factory = create_mock_connector_factory(
            "filesystem", [output_schema], message
        )

        artifacts = {
            "data_a": ArtifactDefinition(
                source=SourceConfig(type="filesystem", properties={})
            ),
            "data_b": ArtifactDefinition(
                source=SourceConfig(type="filesystem", properties={})
            ),
        }
        plan = create_simple_plan(
            artifacts,
            {
                "data_a": (None, output_schema),
                "data_b": (None, output_schema),
            },
        )

        registry = MagicMock(spec=ComponentRegistry)
        registry.container = container
        registry.connector_factories = {"filesystem": connector_factory}
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert - use run_id from result to query the store
        stored_ids = asyncio.run(store.list_keys(result.run_id))
        assert "data_a" in stored_ids
        assert "data_b" in stored_ids

    def test_execution_result_contains_duration(self) -> None:
        """ExecutionResult.total_duration_seconds is populated."""
        # Arrange
        output_schema = Schema("standard_input", "1.0.0")
        message = create_test_message({"files": []})
        connector_factory = create_mock_connector_factory(
            "filesystem", [output_schema], message
        )

        artifacts = {
            "data": ArtifactDefinition(
                source=SourceConfig(type="filesystem", properties={})
            )
        }
        plan = create_simple_plan(artifacts, {"data": (None, output_schema)})

        registry = create_mock_registry(
            with_container=True, connector_factories={"filesystem": connector_factory}
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert
        assert result.total_duration_seconds > 0

    def test_artifact_result_contains_duration(self) -> None:
        """Each Message's extensions.execution.duration_seconds is populated."""
        # Arrange
        output_schema = Schema("standard_input", "1.0.0")
        message = create_test_message({"files": []})
        connector_factory = create_mock_connector_factory(
            "filesystem", [output_schema], message
        )

        artifacts = {
            "data": ArtifactDefinition(
                source=SourceConfig(type="filesystem", properties={})
            )
        }
        plan = create_simple_plan(artifacts, {"data": (None, output_schema)})

        registry = create_mock_registry(
            with_container=True, connector_factories={"filesystem": connector_factory}
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert - load artifact from store to check duration
        store = registry.container.get_service(ArtifactStore)
        stored = asyncio.run(store.get(result.run_id, "data"))
        duration = stored.execution_duration
        assert duration is not None and duration >= 0

    def test_execution_result_contains_valid_run_id(self) -> None:
        """ExecutionResult.run_id is a valid UUID."""
        from uuid import UUID

        # Arrange
        output_schema = Schema("standard_input", "1.0.0")
        message = create_test_message({"files": []})
        connector_factory = create_mock_connector_factory(
            "filesystem", [output_schema], message
        )

        artifacts = {
            "data": ArtifactDefinition(
                source=SourceConfig(type="filesystem", properties={})
            )
        }
        plan = create_simple_plan(artifacts, {"data": (None, output_schema)})

        registry = create_mock_registry(
            with_container=True, connector_factories={"filesystem": connector_factory}
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert - can parse as UUID without error
        uuid_obj = UUID(result.run_id)
        assert str(uuid_obj) == result.run_id

    def test_execution_result_contains_iso8601_timestamp(self) -> None:
        """ExecutionResult.start_timestamp is ISO8601 format with timezone."""
        from datetime import datetime

        # Arrange
        output_schema = Schema("standard_input", "1.0.0")
        message = create_test_message({"files": []})
        connector_factory = create_mock_connector_factory(
            "filesystem", [output_schema], message
        )

        artifacts = {
            "data": ArtifactDefinition(
                source=SourceConfig(type="filesystem", properties={})
            )
        }
        plan = create_simple_plan(artifacts, {"data": (None, output_schema)})

        registry = create_mock_registry(
            with_container=True, connector_factories={"filesystem": connector_factory}
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert - can parse as ISO8601 with timezone
        timestamp = datetime.fromisoformat(result.start_timestamp)
        assert timestamp.tzinfo is not None


# =============================================================================
# Timeout Behaviour
# =============================================================================


class TestDAGExecutorTimeout:
    """Tests for timeout behaviour in DAGExecutor."""

    def test_timeout_marks_remaining_as_skipped(self) -> None:
        """When timeout exceeded, remaining artifacts marked as skipped."""
        output_schema = Schema("standard_input", "1.0.0")

        def slow_extract(*args: Any, **kwargs: Any) -> Any:
            """Slow connector that takes 2 seconds."""
            time.sleep(2)
            return create_test_message({"files": []})

        # Create slow connector factory
        connector_factory = MagicMock()
        mock_class = MagicMock()
        mock_class.get_name.return_value = "slow"
        mock_class.get_supported_output_schemas.return_value = [output_schema]
        connector_factory.component_class = mock_class
        mock_connector = MagicMock()
        mock_connector.extract.side_effect = slow_extract
        connector_factory.create.return_value = mock_connector

        # Create multiple artifacts - with short timeout only some will complete
        artifacts = {
            f"data_{i}": ArtifactDefinition(
                source=SourceConfig(type="slow", properties={})
            )
            for i in range(5)
        }
        artifact_schemas: dict[str, tuple[Schema | None, Schema]] = {
            f"data_{i}": (None, output_schema) for i in range(5)
        }
        # Set 1 second timeout - connectors take 2s each, so timeout will occur
        plan = create_simple_plan(
            artifacts,
            artifact_schemas,
            runbook_config=RunbookConfig(timeout=1),
        )

        registry = create_mock_registry(
            with_container=True, connector_factories={"slow": connector_factory}
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert - some should be skipped due to timeout
        assert len(result.skipped) > 0, (
            "Some artifacts should be skipped due to timeout"
        )
        total = len(result.completed) + len(result.failed) + len(result.skipped)
        assert total == 5, "All artifacts should be accounted for"
