"""Tests for PendingProcessingError handling on the regular path (post-migration).

After the Distributed Processor Protocol migration, PendingProcessingError is no
longer special-cased on the regular (non-distributed) path. Regular processors are
synchronous — any exception is treated as failure. The distributed path handles
batch pending via PendingBatchError in _dispatch_all.
"""

from waivern_core.errors import PendingProcessingError
from waivern_core.schemas import Schema

from waivern_orchestration.executor import DAGExecutor
from waivern_orchestration.models import ArtifactDefinition, SourceConfig

from .test_executor_state import create_failing_connector_factory
from .test_helpers import (
    create_mock_connector_factory,
    create_mock_registry,
    create_simple_plan,
    create_test_message,
)


class TestPendingProcessingErrorOnRegularPath:
    """PendingProcessingError from regular connectors/processors is treated as failure."""

    async def test_pending_processing_error_treated_as_failure(self) -> None:
        """PendingProcessingError from a connector is treated as a regular failure.

        Post-migration, only the distributed dispatch path handles pending
        state. Regular connectors raising PendingProcessingError fail normally.
        """
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

        result = await executor.execute(plan)

        # PendingProcessingError is now treated as failure, not pending
        assert "data" in result.failed
        assert "data" not in result.completed

    async def test_independent_branches_continue_after_pending_error_failure(
        self,
    ) -> None:
        """Independent branches continue executing after PendingProcessingError failure.

        The failed artifact's dependents are skipped, but independent
        artifacts at the same level continue normally.
        """
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
                "derived_c": ([output_schema], output_schema),
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

        result = await executor.execute(plan)

        # source_a failed, source_b completed, derived_c skipped (dep on failed source_a)
        assert "source_a" in result.failed
        assert "source_b" in result.completed
        assert "derived_c" in result.skipped

    async def test_multiple_pending_errors_all_treated_as_failure(self) -> None:
        """Multiple PendingProcessingErrors in the same batch all treated as failures."""
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

        result = await executor.execute(plan)

        assert "source_a" in result.failed
        assert "source_b" in result.failed
