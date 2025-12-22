"""Tests for DAGExecutor child runbook handling - aliases, origin tracking, redaction."""

import asyncio
from typing import Any
from unittest.mock import MagicMock

import pytest
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
# Child Runbook Aliases
# =============================================================================


class TestExecutorChildRunbookAliases:
    """Tests for executor handling of flattened child runbook plans."""

    def test_execute_flattened_plan_with_aliases(self) -> None:
        """Executor correctly handles flattened plan with aliases.

        When a child runbook is flattened, its artifacts get namespaced IDs.
        The executor should execute these namespaced artifacts successfully.
        """
        # Arrange: Simulate a flattened plan where child artifact is namespaced
        # Parent originally had "findings" which maps to child's namespaced artifact
        output_schema = Schema("standard_input", "1.0.0")
        message = create_test_message({"files": [{"path": "test.txt"}]})

        connector_factory = create_mock_connector_factory(
            "filesystem", [output_schema], message
        )

        # Namespaced artifact ID (as produced by flattener)
        namespaced_id = "analyser__abc123__data"

        artifacts = {
            namespaced_id: ArtifactDefinition(
                source=SourceConfig(type="filesystem", properties={})
            ),
        }
        # Alias maps parent's expected name to namespaced child artifact
        aliases = {"findings": namespaced_id}

        plan = create_simple_plan(
            artifacts,
            {namespaced_id: (None, output_schema)},
            aliases=aliases,
        )

        registry = create_mock_registry(
            with_container=True, connector_factories={"filesystem": connector_factory}
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert - namespaced artifact executes successfully
        assert namespaced_id in result.artifacts
        assert result.artifacts[namespaced_id].is_success
        assert result.artifacts[namespaced_id].content == message.content

    def test_execute_downstream_references_namespaced_artifact(self) -> None:
        """Downstream artifacts can reference namespaced artifact IDs.

        After flattening, downstream artifacts reference namespaced IDs directly.
        """
        source_schema = Schema("standard_input", "1.0.0")
        output_schema = Schema("finding", "1.0.0")

        source_message = create_test_message({"files": [{"content": "test"}]})
        processed_message = Message(
            id="processed",
            content={"findings": [{"type": "email"}]},
            schema=output_schema,
        )

        connector_factory = create_mock_connector_factory(
            "filesystem", [source_schema], source_message
        )

        processor_factory = MagicMock()
        mock_processor_class = MagicMock()
        mock_processor_class.get_name.return_value = "analyser"
        mock_processor_class.get_supported_output_schemas.return_value = [output_schema]
        processor_factory.component_class = mock_processor_class
        mock_processor = MagicMock()
        mock_processor.process.return_value = processed_message
        processor_factory.create.return_value = mock_processor

        # Namespaced child artifact
        namespaced_source = "child__xyz789__data"

        artifacts = {
            namespaced_source: ArtifactDefinition(
                source=SourceConfig(type="filesystem", properties={})
            ),
            # Parent artifact that references the namespaced child output
            "analysis": ArtifactDefinition(
                inputs=namespaced_source,
                process=ProcessConfig(type="analyser", properties={}),
            ),
        }

        plan = create_simple_plan(
            artifacts,
            {
                namespaced_source: (None, source_schema),
                "analysis": (source_schema, output_schema),
            },
            aliases={"child_data": namespaced_source},
        )

        registry = create_mock_registry(
            with_container=True,
            connector_factories={"filesystem": connector_factory},
            processor_factories={"analyser": processor_factory},
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert - both artifacts execute successfully
        assert result.artifacts[namespaced_source].is_success
        assert result.artifacts["analysis"].is_success
        assert result.artifacts["analysis"].content == processed_message.content


# =============================================================================
# Origin Tracking
# =============================================================================


class TestExecutorOriginTracking:
    """Tests for origin tracking in artifact results.

    When child runbooks are flattened, their artifacts are namespaced with
    the format: {runbook_name}__{uuid}__{artifact_id}

    The executor should:
    - Set origin='parent' for regular artifacts (no __ in ID)
    - Set origin='child:{runbook_name}' for namespaced artifacts
    - Set alias field for artifacts that have entries in plan.aliases
    """

    def test_execute_artifact_origin_parent(self) -> None:
        """Parent artifacts have origin='parent' in results."""
        output_schema = Schema("standard_input", "1.0.0")
        message = create_test_message({"files": []})

        connector_factory = create_mock_connector_factory(
            "filesystem", [output_schema], message
        )

        # Regular artifact ID (no namespacing)
        artifacts = {
            "data": ArtifactDefinition(
                source=SourceConfig(type="filesystem", properties={})
            ),
        }
        plan = create_simple_plan(artifacts, {"data": (None, output_schema)})

        registry = create_mock_registry(
            with_container=True, connector_factories={"filesystem": connector_factory}
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert - parent artifact has origin='parent'
        assert result.artifacts["data"].is_success
        assert result.artifacts["data"].execution_origin == "parent"
        assert result.artifacts["data"].execution_alias is None

    def test_execute_artifact_origin_child(self) -> None:
        """Child artifacts have origin='child:{name}' in results."""
        output_schema = Schema("standard_input", "1.0.0")
        message = create_test_message({"files": []})

        connector_factory = create_mock_connector_factory(
            "filesystem", [output_schema], message
        )

        # Namespaced artifact ID from child runbook "analyser"
        namespaced_id = "analyser__abc123__data"

        artifacts = {
            namespaced_id: ArtifactDefinition(
                source=SourceConfig(type="filesystem", properties={})
            ),
        }
        plan = create_simple_plan(artifacts, {namespaced_id: (None, output_schema)})

        registry = create_mock_registry(
            with_container=True, connector_factories={"filesystem": connector_factory}
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert - child artifact has origin='child:analyser'
        assert result.artifacts[namespaced_id].is_success
        assert result.artifacts[namespaced_id].execution_origin == "child:analyser"

    def test_execute_artifact_alias_populated(self) -> None:
        """Aliased artifacts have alias field populated in results."""
        output_schema = Schema("standard_input", "1.0.0")
        message = create_test_message({"files": []})

        connector_factory = create_mock_connector_factory(
            "filesystem", [output_schema], message
        )

        # Namespaced child artifact with alias
        namespaced_id = "child_runbook__def456__findings"

        artifacts = {
            namespaced_id: ArtifactDefinition(
                source=SourceConfig(type="filesystem", properties={})
            ),
        }
        # Alias maps "results" to the namespaced artifact
        aliases = {"results": namespaced_id}

        plan = create_simple_plan(
            artifacts,
            {namespaced_id: (None, output_schema)},
            aliases=aliases,
        )

        registry = create_mock_registry(
            with_container=True, connector_factories={"filesystem": connector_factory}
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert - artifact has alias field populated
        assert result.artifacts[namespaced_id].is_success
        assert result.artifacts[namespaced_id].execution_alias == "results"

    def test_execute_mixed_parent_and_child_artifacts(self) -> None:
        """Execution correctly tracks origin for mixed parent/child artifacts."""
        output_schema = Schema("standard_input", "1.0.0")
        message = create_test_message({"files": []})

        connector_factory = create_mock_connector_factory(
            "filesystem", [output_schema], message
        )

        # Mix of parent and child artifacts
        parent_id = "source_data"
        child_id = "processor__ghi789__output"

        artifacts = {
            parent_id: ArtifactDefinition(
                source=SourceConfig(type="filesystem", properties={})
            ),
            child_id: ArtifactDefinition(
                source=SourceConfig(type="filesystem", properties={})
            ),
        }
        aliases = {"processed_results": child_id}

        plan = create_simple_plan(
            artifacts,
            {
                parent_id: (None, output_schema),
                child_id: (None, output_schema),
            },
            aliases=aliases,
        )

        registry = create_mock_registry(
            with_container=True, connector_factories={"filesystem": connector_factory}
        )
        executor = DAGExecutor(registry)

        # Act
        result = asyncio.run(executor.execute(plan))

        # Assert - parent has origin='parent', child has origin='child:processor'
        assert result.artifacts[parent_id].execution_origin == "parent"
        assert result.artifacts[parent_id].execution_alias is None

        assert result.artifacts[child_id].execution_origin == "child:processor"
        assert result.artifacts[child_id].execution_alias == "processed_results"


# =============================================================================
# Sensitive Input Redaction (Placeholder)
# =============================================================================


class TestExecutorSensitiveInputRedaction:
    """Tests for sensitive input redaction in logs and results.

    When child runbooks declare inputs with sensitive=True, the executor should:
    - Replace values with [REDACTED] in log messages
    - Exclude sensitive values from execution result JSON
    - Still pass actual values to processors for execution

    Note: Sensitive input tracking is communicated from flattener to executor
    via the ExecutionPlan's metadata about which artifacts handle sensitive data.

    These tests are placeholders for Phase 3+ implementation. The current
    executor does not yet implement sensitive input redaction.
    """

    def test_sensitive_input_redacted_from_logs(self, caplog: Any) -> None:
        """Sensitive input values are replaced with [REDACTED] in logs.

        When an artifact processes sensitive input data, log messages should
        not contain the actual values - they should show [REDACTED] instead.

        This test is a placeholder - implementation deferred to Phase 3+.
        """
        # This test documents expected behavior for sensitive input redaction
        # The feature is not yet implemented, so we skip for now
        pytest.skip("Sensitive input redaction not yet implemented")

        # Expected behavior when implemented:
        # - Create plan with artifact marked as handling sensitive input
        # - Execute the plan with DEBUG logging enabled
        # - Verify log messages contain [REDACTED] instead of actual values
        # - Verify processor still receives actual values

    def test_sensitive_input_redacted_from_execution_results(self) -> None:
        """Sensitive input values are not included in JSON execution results.

        When serialising ExecutionResult to JSON for output, any sensitive
        input values should be excluded or masked.

        This test is a placeholder - implementation deferred to Phase 3+.
        """
        pytest.skip("Sensitive input redaction not yet implemented")

        # Expected behavior when implemented:
        # - Create plan with artifact handling sensitive input
        # - Execute the plan
        # - Serialise result to JSON
        # - Verify sensitive data is not present in JSON output

    def test_sensitive_input_passed_to_processor(self) -> None:
        """Processors receive actual sensitive values, not redacted ones.

        While logs and results should be redacted, the actual processor
        needs to receive the real values to perform its work.

        This test is a placeholder - implementation deferred to Phase 3+.
        """
        pytest.skip("Sensitive input redaction not yet implemented")

        # Expected behavior when implemented:
        # - Create plan with artifact handling sensitive input
        # - Execute with mock processor that captures input
        # - Verify processor received actual value (not [REDACTED])
        # - Verify logs show [REDACTED]
