"""Tests for artifact reuse from previous runs."""

from waivern_artifact_store import ArtifactStore
from waivern_core.schemas import Schema

from waivern_orchestration.executor import DAGExecutor
from waivern_orchestration.models import ArtifactDefinition, ReuseConfig

from .test_helpers import (
    create_message_with_execution,
    create_mock_registry,
    create_simple_plan,
)

# =============================================================================
# Artifact Reuse Tests
# =============================================================================


class TestExecutorReuse:
    """Tests for artifact reuse from previous runs."""

    async def test_reuse_artifact_copies_from_previous_run(self) -> None:
        """Reused artifact is loaded from source run and saved to new run.

        Verifies:
        - Content is copied correctly from source run
        - Artifact appears in completed set
        - Source field indicates reuse origin (reuse:{run_id}/{artifact_id})

        """
        # Arrange: Create registry with real store
        registry = create_mock_registry(with_container=True)
        store = registry.container.get_service(ArtifactStore)
        executor = DAGExecutor(registry)

        # Create a "previous run" with an artifact
        previous_run_id = "previous-run-123"
        source_artifact_id = "source_data"
        original_content = {"files": [{"path": "test.txt", "content": "hello world"}]}
        original_message = create_message_with_execution(
            content=original_content,
            schema=Schema("standard_input", "1.0.0"),
            status="success",
        )
        await store.save(previous_run_id, source_artifact_id, original_message)

        # Create plan with reuse artifact
        artifacts = {
            "reused_data": ArtifactDefinition(
                reuse=ReuseConfig(
                    from_run=previous_run_id,
                    artifact=source_artifact_id,
                )
            )
        }
        output_schema = Schema("standard_input", "1.0.0")
        artifact_schemas: dict[str, tuple[Schema | None, Schema]] = {
            "reused_data": (None, output_schema)
        }
        plan = create_simple_plan(artifacts, artifact_schemas)

        # Act
        result = await executor.execute(plan)

        # Assert - artifact should be completed
        assert "reused_data" in result.completed
        assert len(result.failed) == 0
        assert len(result.skipped) == 0

        # Assert - content should be copied to new run
        stored = await store.get(result.run_id, "reused_data")
        assert stored.content == original_content

        # Assert - source should indicate reuse origin
        expected_source = f"reuse:{previous_run_id}/{source_artifact_id}"
        assert stored.source == expected_source

    async def test_reuse_artifact_not_found_marks_as_failed(self) -> None:
        """When source artifact doesn't exist, artifact is marked as failed."""
        # Arrange: Create registry with real store (no previous run data)
        registry = create_mock_registry(with_container=True)
        executor = DAGExecutor(registry)

        # Create plan with reuse artifact pointing to non-existent run/artifact
        artifacts = {
            "reused_data": ArtifactDefinition(
                reuse=ReuseConfig(
                    from_run="nonexistent-run",
                    artifact="nonexistent_artifact",
                )
            )
        }
        output_schema = Schema("standard_input", "1.0.0")
        artifact_schemas: dict[str, tuple[Schema | None, Schema]] = {
            "reused_data": (None, output_schema)
        }
        plan = create_simple_plan(artifacts, artifact_schemas)

        # Act
        result = await executor.execute(plan)

        # Assert - artifact should be failed, not completed
        assert "reused_data" in result.failed
        assert "reused_data" not in result.completed
