"""Tests for artifact classification in DAGExecutor.

These tests verify that the executor correctly separates ready artifacts
into regular, distributed, and resuming groups based on their definition
and execution state. Tested end-to-end through execute().

Stubs written in Step 1; implementations added in Step 5 when the
three-phase orchestration is integrated into _execute_dag.
"""


# =============================================================================
# Classification Tests
# =============================================================================


class TestClassifyArtifacts:
    """Tests for artifact classification in DAGExecutor."""

    async def test_source_artifact_classified_as_regular(self) -> None:
        """Source artifact (has SourceConfig) is classified as regular."""
        pass

    async def test_reuse_artifact_classified_as_regular(self) -> None:
        """Reuse artifact (has ReuseConfig) is classified as regular."""
        pass

    async def test_passthrough_artifact_classified_as_regular(self) -> None:
        """Passthrough artifact (inputs, no process) is classified as regular."""
        pass

    async def test_regular_processor_classified_as_regular(self) -> None:
        """Processor not implementing DistributedProcessor is classified as regular."""
        pass

    async def test_distributed_processor_classified_as_distributed(self) -> None:
        """Processor implementing DistributedProcessor is classified as distributed."""
        pass

    async def test_pending_artifact_classified_as_resuming(self) -> None:
        """Pending artifact is classified as resuming with PrepareResult loaded."""
        pass

    async def test_mixed_level_classifies_all_types_correctly(self) -> None:
        """Mixed level with all artifact types classifies each correctly."""
        pass
