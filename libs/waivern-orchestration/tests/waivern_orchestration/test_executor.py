"""Tests for DAGExecutor - core execution behaviour.

For concurrency, observability, and timeout tests, see test_executor_concurrency.py.
For child runbook handling tests, see test_executor_child_runbooks.py.
"""

import asyncio
from typing import Any
from unittest.mock import MagicMock

from waivern_artifact_store import ArtifactStore
from waivern_core import Message
from waivern_core.schemas import Schema

from waivern_orchestration.executor import DAGExecutor
from waivern_orchestration.models import (
    ArtifactDefinition,
    ProcessConfig,
    SourceConfig,
)

from .test_helpers import (
    create_mock_connector_factory,
    create_mock_registry,
    create_simple_plan,
    create_test_message,
)

# =============================================================================
# Core Execution Tests - Happy Path, Dependencies, Fan-In
# =============================================================================


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

        # Assert - check result summary and load artifact from store
        assert "data" in result.completed
        assert len(result.skipped) == 0
        store = registry.container.get_service(ArtifactStore)
        stored = asyncio.run(store.get(result.run_id, "data"))
        assert stored.is_success
        assert stored.content == expected_message.content


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
        assert {"a", "b", "c"} == result.completed
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
        assert {"artifact_a", "artifact_b"} == result.completed
        store = registry.container.get_service(ArtifactStore)
        stored_a = asyncio.run(store.get(result.run_id, "artifact_a"))
        stored_b = asyncio.run(store.get(result.run_id, "artifact_b"))
        assert stored_a.content == message_a.content
        assert stored_b.content == message_b.content


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
        assert {"source_a", "source_b"} == result.completed
        assert "merged" in result.failed
        store = registry.container.get_service(ArtifactStore)
        merged = asyncio.run(store.get(result.run_id, "merged"))
        assert not merged.is_success
        assert merged.execution_error is not None
        assert "not yet implemented" in (merged.execution_error or "")


# =============================================================================
# Error Handling
# =============================================================================


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
        assert "source" in result.failed
        assert "dependent" in result.skipped
        store = registry.container.get_service(ArtifactStore)
        source_msg = asyncio.run(store.get(result.run_id, "source"))
        assert not source_msg.is_success
        assert source_msg.execution_error is not None
        assert "Connection failed" in (source_msg.execution_error or "")

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
        assert "optional_data" in result.failed
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
        assert "data" in result.failed
        store = registry.container.get_service(ArtifactStore)
        data_msg = asyncio.run(store.get(result.run_id, "data"))
        assert not data_msg.is_success
        assert data_msg.execution_error is not None
        assert "nonexistent_connector" in (data_msg.execution_error or "")


# =============================================================================
# Process (Processor) Execution
# =============================================================================


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
        assert {"source", "findings"} == result.completed
        store = registry.container.get_service(ArtifactStore)
        findings_msg = asyncio.run(store.get(result.run_id, "findings"))
        assert findings_msg.is_success
        assert findings_msg.content == processed_message.content
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
        assert "source_data" in result.completed
        assert "processed" in result.failed
        store = registry.container.get_service(ArtifactStore)
        processed_msg = asyncio.run(store.get(result.run_id, "processed"))
        assert not processed_msg.is_success
        assert processed_msg.execution_error is not None
        assert "nonexistent_processor" in (processed_msg.execution_error or "")


# =============================================================================
# Artifact Metadata (run_id, source, extensions)
# =============================================================================


class TestDAGExecutorArtifactMetadata:
    """Tests for artifact metadata population (run_id, source, extensions)."""

    def test_stored_artifact_has_run_id(self) -> None:
        """Stored artifact includes run_id for correlation."""
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

        # Assert - run_id should be set on the result and match stored artifact
        assert result.run_id is not None
        store = registry.container.get_service(ArtifactStore)
        stored = asyncio.run(store.get(result.run_id, "data"))
        assert stored.run_id == result.run_id

    def test_stored_artifact_has_source_for_connector(self) -> None:
        """Stored artifact has source field indicating connector type."""
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

        # Assert - source should be "connector:filesystem"
        store = registry.container.get_service(ArtifactStore)
        stored = asyncio.run(store.get(result.run_id, "data"))
        assert stored.source == "connector:filesystem"

    def test_stored_artifact_has_source_for_processor(self) -> None:
        """Stored artifact has source field indicating processor type."""
        source_schema = Schema("standard_input", "1.0.0")
        output_schema = Schema("personal_data_finding", "1.0.0")

        source_message = create_test_message({"files": []})
        processed_message = Message(
            id="processed",
            content={"findings": []},
            schema=output_schema,
        )

        connector_factory = create_mock_connector_factory(
            "filesystem", [source_schema], source_message
        )

        processor_factory = MagicMock()
        mock_processor_class = MagicMock()
        mock_processor_class.get_name.return_value = "personal_data"
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
                process=ProcessConfig(type="personal_data", properties={}),
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
            processor_factories={"personal_data": processor_factory},
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert - source should be "processor:personal_data"
        store = registry.container.get_service(ArtifactStore)
        stored = asyncio.run(store.get(result.run_id, "findings"))
        assert stored.source == "processor:personal_data"

    def test_stored_artifact_has_execution_context(self) -> None:
        """Stored artifact includes ExecutionContext with status and duration."""
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

        # Assert - extensions.execution should be populated
        store = registry.container.get_service(ArtifactStore)
        stored = asyncio.run(store.get(result.run_id, "data"))

        assert stored.extensions is not None
        assert stored.extensions.execution is not None
        assert stored.extensions.execution.status == "success"
        assert stored.extensions.execution.duration_seconds is not None
        assert stored.extensions.execution.duration_seconds >= 0
