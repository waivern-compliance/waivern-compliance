"""Tests for artifact classification and dispatch in DAGExecutor.

These tests verify end-to-end through execute() that the executor correctly:
- Separates ready artifacts into regular, distributed, and resuming groups
- Groups dispatch requests by type and routes results back
- Handles PendingBatchError and dispatch failures

Stubs written in Steps 1 and 3; implementations added in Step 5 when the
three-phase orchestration is integrated into _execute_dag.
"""


# =============================================================================
# Classification Tests
# =============================================================================


class TestClassifyArtifacts:
    """Tests for artifact classification in DAGExecutor.

    Verified end-to-end: the classification outcome is observable by which
    code path executes (connector extract vs processor prepare/finalise).
    """

    async def test_source_artifact_classified_as_regular(self) -> None:
        """Source artifact (has SourceConfig) is classified as regular.

        Arrange: single source artifact with a connector factory.
        Assert: connector.extract() is called (not prepare/finalise).
        """
        pass

    async def test_reuse_artifact_classified_as_regular(self) -> None:
        """Reuse artifact (has ReuseConfig) is classified as regular.

        Arrange: reuse artifact referencing a previous run.
        Assert: artifact loaded from previous run (not prepare/finalise).
        """
        pass

    async def test_passthrough_artifact_classified_as_regular(self) -> None:
        """Passthrough artifact (inputs, no process) is classified as regular.

        Arrange: artifact with inputs but no process config.
        Assert: input message passed through (not prepare/finalise).
        """
        pass

    async def test_regular_processor_classified_as_regular(self) -> None:
        """Processor not implementing DistributedProcessor is classified as regular.

        Arrange: processor factory returning a Processor-only instance
        (no prepare/finalise methods).
        Assert: processor.process() is called (not prepare/finalise).
        """
        pass

    async def test_distributed_processor_classified_as_distributed(self) -> None:
        """Processor implementing DistributedProcessor is classified as distributed.

        Arrange: processor factory returning a dual-protocol instance
        (implements both Processor and DistributedProcessor).
        Assert: prepare() is called, then finalise() with dispatch results.
        process() is NOT called.
        """
        pass

    async def test_pending_artifact_classified_as_resuming(self) -> None:
        """Pending artifact is classified as resuming with PrepareResult loaded.

        Arrange: execution state with artifact in pending set; PrepareResult
        persisted in store from a previous interrupted run.
        Assert: deserialise_prepare_result() called with raw dict from store,
        then dispatch (Phase 2) and finalise (Phase 3) — no prepare (Phase 1).
        """
        pass

    async def test_mixed_level_classifies_all_types_correctly(self) -> None:
        """Mixed level with all artifact types classifies each correctly.

        Arrange: level with source, reuse, passthrough, regular processor,
        distributed processor, and resuming artifact.
        Assert: each artifact follows its expected code path; regular and
        distributed artifacts execute concurrently in the same gather.
        """
        pass


# =============================================================================
# Dispatch Tests
# =============================================================================


class TestDispatchAll:
    """Tests for dispatch grouping, routing, and error handling.

    Verified end-to-end: dispatch behaviour is observable through the
    final execution result (completed/failed/pending) and store state.
    """

    async def test_requests_grouped_by_type_and_dispatched(self) -> None:
        """Requests from multiple artifacts of the same type are grouped.

        Arrange: two distributed processors at the same level, both
        producing LLMRequest objects.
        Assert: dispatcher.dispatch() called once with all requests
        combined, not once per artifact.
        """
        pass

    async def test_results_routed_back_to_correct_artifacts(self) -> None:
        """Dispatch results are routed to the correct artifact via request_id.

        Arrange: two distributed processors each producing requests with
        distinct request_ids. Dispatcher returns results with matching ids.
        Assert: each processor's finalise() receives only its own results,
        not the other artifact's results.
        """
        pass

    async def test_pending_batch_error_persists_and_marks_pending(self) -> None:
        """PendingBatchError persists PrepareResult and marks artifacts pending.

        Arrange: dispatcher raises PendingBatchError.
        Assert:
        - PrepareResult serialised via model_dump(mode="json") and saved
          to store via save_prepared()
        - Artifact marked pending in ExecutionState
        - Run status is "interrupted" (not failed)
        - Artifact NOT in completed, failed, or skipped
        """
        pass

    async def test_dispatch_error_fails_affected_artifacts_only(self) -> None:
        """Non-pending dispatch errors fail only the affected dispatch group.

        Arrange: two distributed processors at the same level using the
        same request type. Dispatcher raises RuntimeError.
        Assert:
        - Both artifacts in the dispatch group marked as failed
        - Their dependents are skipped
        - Regular artifacts at the same level that already completed
          remain completed (not affected by the dispatch failure)
        """
        pass

    async def test_short_circuited_entries_get_empty_results(self) -> None:
        """Entries with empty requests skip dispatch and get empty results.

        Arrange: distributed processor whose prepare() returns a
        PrepareResult with empty requests list.
        Assert: finalise() called with empty results sequence.
        No dispatcher resolved or called.
        """
        pass

    async def test_mixed_request_types_dispatched_to_different_dispatchers(
        self,
    ) -> None:
        """Mixed request types at the same level dispatch to separate dispatchers.

        Arrange: two distributed processors producing different request
        types (e.g., LLMRequest and a hypothetical HTTPRequest).
        Assert: each request type group dispatched to its own dispatcher.
        Results correctly routed back despite different dispatchers.
        """
        pass
