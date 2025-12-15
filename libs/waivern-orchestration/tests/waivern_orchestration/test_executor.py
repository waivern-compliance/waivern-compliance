"""Tests for DAGExecutor."""

import asyncio
from typing import Any
from unittest.mock import MagicMock

from waivern_artifact_store.base import ArtifactStore
from waivern_artifact_store.in_memory import InMemoryArtifactStore
from waivern_core import Message
from waivern_core.schemas import Schema
from waivern_core.services import ComponentRegistry, ServiceContainer, ServiceDescriptor

from waivern_orchestration.executor import DAGExecutor
from waivern_orchestration.models import (
    ArtifactDefinition,
    ProcessConfig,
    RunbookConfig,
    SourceConfig,
)

from .test_helpers import (
    create_mock_connector_factory,
    create_mock_registry,
    create_simple_plan,
    create_test_message,
)


class TestDAGExecutorHappyPath:
    """Happy path tests for DAGExecutor."""

    def test_execute_single_source_artifact(self) -> None:
        """Execute a single source artifact (connector) successfully."""
        # Arrange: Create mock connector that returns a message
        output_schema = Schema("standard_input", "1.0.0")
        expected_message = create_test_message(
            {"files": [{"path": "test.txt", "content": "hello"}]}
        )

        connector_factory = create_mock_connector_factory(
            "filesystem", [output_schema], expected_message
        )

        # Create plan with single source artifact
        artifacts = {
            "data": ArtifactDefinition(
                source=SourceConfig(type="filesystem", properties={"path": "/tmp"})
            )
        }
        artifact_schemas: dict[str, tuple[Schema | None, Schema]] = {
            "data": (None, output_schema)
        }
        plan = create_simple_plan(artifacts, artifact_schemas)

        # Create registry with mock factories
        registry = create_mock_registry(
            with_container=True,
            connector_factories={"filesystem": connector_factory},
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert
        assert "data" in result.artifacts
        assert result.artifacts["data"].success is True
        assert result.artifacts["data"].message == expected_message
        assert len(result.skipped) == 0


class TestDAGExecutorDependencies:
    """Tests for dependency ordering in DAGExecutor."""

    def test_execute_chain_respects_dependency_order(self) -> None:
        """Artifacts in a chain (A -> B -> C) execute in correct dependency order."""
        # Arrange - track execution order via side effects
        execution_order: list[str] = []

        output_schema = Schema("standard_input", "1.0.0")
        message = create_test_message({"files": []})

        def create_tracking_factory(name: str) -> MagicMock:
            """Create a factory that tracks when its connector is called."""
            factory = MagicMock()
            mock_class = MagicMock()
            mock_class.get_name.return_value = name
            mock_class.get_supported_output_schemas.return_value = [output_schema]
            factory.component_class = mock_class

            mock_connector = MagicMock()

            def track_extract(*args: Any, **kwargs: Any) -> Message:
                execution_order.append(name)
                return message

            mock_connector.extract.side_effect = track_extract
            factory.create.return_value = mock_connector
            return factory

        connector_factory = create_tracking_factory("source")

        # A is a source, B depends on A, C depends on B
        artifacts = {
            "a": ArtifactDefinition(source=SourceConfig(type="source", properties={})),
            "b": ArtifactDefinition(inputs="a"),  # Passthrough depends on A
            "c": ArtifactDefinition(inputs="b"),  # Passthrough depends on B
        }
        plan = create_simple_plan(
            artifacts,
            {
                "a": (None, output_schema),
                "b": (output_schema, output_schema),  # input from A, output same
                "c": (output_schema, output_schema),  # input from B, output same
            },
        )

        registry = create_mock_registry(
            with_container=True, connector_factories={"source": connector_factory}
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert - A must execute before B, B must execute before C
        assert result.artifacts["a"].success is True
        assert result.artifacts["b"].success is True
        assert result.artifacts["c"].success is True
        # A runs first (it's the only connector)
        assert execution_order[0] == "source"

    def test_execute_parallel_independent_artifacts(self) -> None:
        """Independent artifacts execute in parallel, both completing successfully."""
        # Arrange - two independent source artifacts
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

        registry = create_mock_registry(
            with_container=True,
            connector_factories={"source_a": factory_a, "source_b": factory_b},
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert - both artifacts completed successfully
        assert result.artifacts["artifact_a"].success is True
        assert result.artifacts["artifact_b"].success is True
        assert result.artifacts["artifact_a"].message == message_a
        assert result.artifacts["artifact_b"].message == message_b


class TestDAGExecutorFanIn:
    """Tests for fan-in behaviour in DAGExecutor."""

    def test_execute_fan_in_sources_succeed_merge_not_implemented(self) -> None:
        """Fan-in: sources succeed but merge raises NotImplementedError."""
        # Arrange - two sources feeding into one merged artifact
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
            "source_a": ArtifactDefinition(
                source=SourceConfig(type="source_a", properties={})
            ),
            "source_b": ArtifactDefinition(
                source=SourceConfig(type="source_b", properties={})
            ),
            "merged": ArtifactDefinition(
                inputs=["source_a", "source_b"]  # Fan-in from both sources
            ),
        }
        plan = create_simple_plan(
            artifacts,
            {
                "source_a": (None, output_schema),
                "source_b": (None, output_schema),
                "merged": (output_schema, output_schema),
            },
        )

        registry = create_mock_registry(
            with_container=True,
            connector_factories={"source_a": factory_a, "source_b": factory_b},
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert - sources succeed, but merge fails (not yet implemented)
        assert result.artifacts["source_a"].success is True
        assert result.artifacts["source_b"].success is True
        assert result.artifacts["merged"].success is False
        assert result.artifacts["merged"].error is not None
        assert "not yet implemented" in result.artifacts["merged"].error


class TestDAGExecutorErrorHandling:
    """Tests for error handling in DAGExecutor."""

    def test_failed_artifact_skips_dependents(self) -> None:
        """When artifact fails, all dependents are marked as skipped."""
        # Arrange - source that fails, with a dependent artifact
        output_schema = Schema("standard_input", "1.0.0")

        # Create a factory that raises an exception
        failing_factory = MagicMock()
        mock_class = MagicMock()
        mock_class.get_name.return_value = "failing_source"
        mock_class.get_supported_output_schemas.return_value = [output_schema]
        failing_factory.component_class = mock_class
        failing_connector = MagicMock()
        failing_connector.extract.side_effect = RuntimeError("Connection failed")
        failing_factory.create.return_value = failing_connector

        artifacts = {
            "source": ArtifactDefinition(
                source=SourceConfig(type="failing_source", properties={})
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
            with_container=True, connector_factories={"failing_source": failing_factory}
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert - source failed, dependent should be skipped
        assert result.artifacts["source"].success is False
        assert result.artifacts["source"].error is not None
        assert "Connection failed" in result.artifacts["source"].error
        assert "dependent" in result.skipped

    def test_optional_artifact_failure_logs_warning(self, caplog: Any) -> None:
        """Optional artifact failure logs warning, not error."""
        import logging

        # Arrange - optional artifact that fails
        output_schema = Schema("standard_input", "1.0.0")

        failing_factory = MagicMock()
        mock_class = MagicMock()
        mock_class.get_name.return_value = "failing"
        mock_class.get_supported_output_schemas.return_value = [output_schema]
        failing_factory.component_class = mock_class
        failing_connector = MagicMock()
        failing_connector.extract.side_effect = RuntimeError("Optional failed")
        failing_factory.create.return_value = failing_connector

        artifacts = {
            "optional_data": ArtifactDefinition(
                source=SourceConfig(type="failing", properties={}),
                optional=True,  # Mark as optional
            ),
        }
        plan = create_simple_plan(artifacts, {"optional_data": (None, output_schema)})

        registry = create_mock_registry(
            with_container=True, connector_factories={"failing": failing_factory}
        )
        executor = DAGExecutor(registry)

        # Act
        with caplog.at_level(logging.WARNING):
            result = asyncio.run(executor.execute(plan))

        # Assert - artifact failed but logged as warning
        assert result.artifacts["optional_data"].success is False
        # Check that a warning was logged (not error)
        assert any("optional" in record.message.lower() for record in caplog.records)

    def test_connector_not_found_returns_error(self) -> None:
        """Missing connector type returns clear error message."""
        # Arrange - reference a connector that doesn't exist
        output_schema = Schema("standard_input", "1.0.0")

        artifacts = {
            "data": ArtifactDefinition(
                source=SourceConfig(type="nonexistent_connector", properties={})
            ),
        }
        plan = create_simple_plan(artifacts, {"data": (None, output_schema)})

        # Registry has no connectors registered
        registry = create_mock_registry(with_container=True, connector_factories={})
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert - should fail with clear error about missing connector
        assert result.artifacts["data"].success is False
        assert result.artifacts["data"].error is not None
        assert "nonexistent_connector" in result.artifacts["data"].error


class TestDAGExecutorProcess:
    """Tests for process (processor) execution in DAGExecutor."""

    def test_execute_derived_with_process(self) -> None:
        """Derived artifact with process executes processor."""
        source_schema = Schema("standard_input", "1.0.0")
        output_schema = Schema("personal_data_finding", "1.0.0")

        source_message = create_test_message({"files": [{"content": "test"}]})
        processed_message = Message(
            id="processed",
            content={"findings": [{"type": "email"}]},
            schema=output_schema,
        )

        connector_factory = create_mock_connector_factory(
            "filesystem", [source_schema], source_message
        )

        # Create mock processor factory with process method
        processor_factory = MagicMock()
        mock_processor_class = MagicMock()
        mock_processor_class.get_name.return_value = "personal_data_analyser"
        mock_processor_class.get_supported_output_schemas.return_value = [output_schema]
        processor_factory.component_class = mock_processor_class
        mock_processor = MagicMock()
        mock_processor.process.return_value = processed_message
        processor_factory.create.return_value = mock_processor

        artifacts = {
            "source": ArtifactDefinition(
                source=SourceConfig(type="filesystem", properties={})
            ),
            "findings": ArtifactDefinition(
                inputs="source",
                process=ProcessConfig(type="personal_data_analyser", properties={}),
            ),
        }
        plan = create_simple_plan(
            artifacts,
            {
                "source": (None, source_schema),
                "findings": (source_schema, output_schema),
            },
        )

        registry = create_mock_registry(
            with_container=True,
            connector_factories={"filesystem": connector_factory},
            processor_factories={"personal_data_analyser": processor_factory},
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert
        assert result.artifacts["source"].success is True
        assert result.artifacts["findings"].success is True
        assert result.artifacts["findings"].message == processed_message
        mock_processor.process.assert_called_once()

    def test_processor_not_found_returns_error(self) -> None:
        """Missing processor type returns clear error message."""
        output_schema = Schema("standard_input", "1.0.0")
        message = create_test_message({"files": []})

        connector_factory = create_mock_connector_factory(
            "source", [output_schema], message
        )

        artifacts = {
            "source_data": ArtifactDefinition(
                source=SourceConfig(type="source", properties={})
            ),
            "processed": ArtifactDefinition(
                inputs="source_data",
                process=ProcessConfig(type="nonexistent_processor", properties={}),
            ),
        }
        plan = create_simple_plan(
            artifacts,
            {
                "source_data": (None, output_schema),
                "processed": (output_schema, output_schema),
            },
        )

        # Registry has no processors
        registry = create_mock_registry(
            with_container=True,
            connector_factories={"source": connector_factory},
            processor_factories={},
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert - source succeeds, processor fails
        assert result.artifacts["source_data"].success is True
        assert result.artifacts["processed"].success is False
        assert result.artifacts["processed"].error is not None
        assert "nonexistent_processor" in result.artifacts["processed"].error


class TestDAGExecutorConcurrency:
    """Tests for concurrency control in DAGExecutor."""

    def test_concurrency_limit_respected(self) -> None:
        """At most max_concurrency artifacts execute simultaneously."""
        import threading
        import time

        # Track concurrent execution count
        current_concurrent = 0
        max_concurrent_observed = 0
        lock = threading.Lock()

        output_schema = Schema("standard_input", "1.0.0")
        message = create_test_message({"files": []})

        def tracking_extract(*args: Any, **kwargs: Any) -> Message:
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
        assert len(result.artifacts) == 5
        assert all(r.success for r in result.artifacts.values())
        assert max_concurrent_observed <= 2, (
            f"Expected max 2 concurrent, but observed {max_concurrent_observed}"
        )


class TestDAGExecutorObservability:
    """Tests for observability features in DAGExecutor."""

    def test_list_artifacts_after_execution(self) -> None:
        """After execution, store.list_artifacts() returns all produced IDs."""
        # Arrange - use singleton store so we can access it after execution

        store = InMemoryArtifactStore()
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
        asyncio.run(executor.execute(plan))

        # Assert
        stored_ids = store.list_artifacts()
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
        """Each ArtifactResult.duration_seconds is populated."""
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
        assert result.artifacts["data"].duration_seconds >= 0

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


class TestDAGExecutorTimeout:
    """Tests for timeout behaviour in DAGExecutor."""

    def test_timeout_marks_remaining_as_skipped(self) -> None:
        """When timeout exceeded, remaining artifacts marked as skipped."""
        import time

        output_schema = Schema("standard_input", "1.0.0")

        def slow_extract(*args: Any, **kwargs: Any) -> Message:
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
        total = len(result.artifacts) + len(result.skipped)
        assert total == 5, "All artifacts should be accounted for"


# =============================================================================
# Phase 3: Child Runbooks - Executor Tests for Aliases and Origin Tracking
# =============================================================================


class TestExecutorChildRunbookAliases:
    """Tests for executor handling of flattened child runbook plans."""

    def test_execute_flattened_plan_with_aliases(self) -> None:
        """Executor correctly handles flattened plan with aliases."""
        pass

    def test_execute_downstream_references_alias(self) -> None:
        """Downstream artifacts can reference aliased artifact names."""
        pass


class TestExecutorOriginTracking:
    """Tests for origin tracking in artifact results."""

    def test_execute_artifact_origin_parent(self) -> None:
        """Parent artifacts have origin='parent' in results."""
        pass

    def test_execute_artifact_origin_child(self) -> None:
        """Child artifacts have origin='child:{name}' in results."""
        pass

    def test_execute_artifact_alias_populated(self) -> None:
        """Aliased artifacts have alias field populated in results."""
        pass


class TestExecutorSensitiveInputRedaction:
    """Tests for sensitive input redaction in logs and results."""

    def test_sensitive_input_redacted_from_logs(self) -> None:
        """Sensitive input values are replaced with [REDACTED] in logs."""
        pass

    def test_sensitive_input_redacted_from_execution_results(self) -> None:
        """Sensitive input values are not included in JSON execution results."""
        pass

    def test_sensitive_input_passed_to_processor(self) -> None:
        """Processors receive actual sensitive values, not redacted ones."""
        pass
