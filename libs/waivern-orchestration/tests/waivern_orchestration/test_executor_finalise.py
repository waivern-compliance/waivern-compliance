"""Tests for distributed processor finalise behaviour and multi-round dispatch.

Verifies end-to-end through execute() that the executor correctly:
- Saves completed distributed artifacts with correct metadata
- Propagates model_name via enrich_execution_context
- Cleans up persisted PrepareResult on completion
- Handles multi-round dispatch-finalise cycles
- Enforces max round limits
"""

from dataclasses import replace
from typing import override
from unittest.mock import AsyncMock

from waivern_artifact_store import ArtifactStore
from waivern_core import ExecutionContext
from waivern_core.dispatch import (
    DispatchRequest,
    DispatchResult,
    PrepareResult,
)
from waivern_core.schemas import Schema

from waivern_orchestration.executor import DAGExecutor
from waivern_orchestration.models import (
    ArtifactDefinition,
    ProcessConfig,
    SourceConfig,
)

from .test_helpers import (
    StubDistributedProcessor,
    StubState,
    create_distributed_processor_factory,
    create_mock_connector_factory,
    create_mock_dispatcher,
    create_mock_registry,
    create_simple_plan,
    create_test_message,
)

# =============================================================================
# Metadata & Cleanup
# =============================================================================


class TestDistributedArtifactMetadata:
    """Tests for metadata on completed distributed artifacts."""

    async def test_message_result_saves_with_correct_metadata(self) -> None:
        """Saved distributed artifact has correct executor metadata.

        Arrange: source → distributed processor completing in one round.
        Assert: saved artifact has run_id, source='processor:{type}',
        ExecutionContext with status='success'.
        """
        source_schema = Schema("standard_input", "1.0.0")
        output_schema = Schema("findings", "1.0.0")
        source_message = create_test_message({"files": []})
        final_message = create_test_message(
            {"findings": ["meta_test"]}, schema=output_schema
        )

        request = DispatchRequest(name="meta_req")
        dispatch_result = DispatchResult(request_id=request.request_id)

        processor = StubDistributedProcessor(
            prepare_result=PrepareResult(state=StubState(), requests=[request]),
            finalise_results=[final_message],
        )

        connector_factory = create_mock_connector_factory(
            "src", [source_schema], source_message
        )
        dispatcher = create_mock_dispatcher([dispatch_result])

        artifacts = {
            "source": ArtifactDefinition(
                source=SourceConfig(type="src", properties={})
            ),
            "findings": ArtifactDefinition(
                inputs="source",
                process=ProcessConfig(type="dist_proc", properties={}),
            ),
        }
        plan = create_simple_plan(
            artifacts,
            {
                "source": (None, source_schema),
                "findings": ([source_schema], output_schema),
            },
        )

        registry = create_mock_registry(
            with_container=True,
            connector_factories={"src": connector_factory},
            processor_factories={
                "dist_proc": create_distributed_processor_factory(
                    "dist_proc", processor
                ),
            },
        )
        registry.get_dispatcher_for.return_value = dispatcher
        executor = DAGExecutor(registry)

        exec_result = await executor.execute(plan)
        assert "findings" in exec_result.completed

        store = registry.container.get_service(ArtifactStore)
        stored = await store.get_artifact(exec_result.run_id, "findings")

        assert stored.run_id == exec_result.run_id
        assert stored.source == "processor:dist_proc"
        assert stored.extensions is not None
        assert stored.extensions.execution is not None
        assert stored.extensions.execution.status == "success"

    async def test_model_name_flows_from_dispatch_result(self) -> None:
        """enrich_execution_context propagates model_name to saved artifact.

        Arrange: dispatcher returns results whose enrich_execution_context
        sets model_name. Processor finalise() returns Message.
        Assert: saved artifact's ExecutionContext.model_name matches
        the value set by the dispatch result.
        """
        source_schema = Schema("standard_input", "1.0.0")
        output_schema = Schema("findings", "1.0.0")
        source_message = create_test_message({"files": []})
        final_message = create_test_message(
            {"findings": ["model_test"]}, schema=output_schema
        )

        request = DispatchRequest(name="model_req")

        # Create a custom DispatchResult that enriches with model_name
        class ModelNameResult(DispatchResult):
            model_name: str

            @override
            def enrich_execution_context(
                self, context: ExecutionContext
            ) -> ExecutionContext:
                return replace(context, model_name=self.model_name)

        dispatch_result = ModelNameResult(
            request_id=request.request_id,
            model_name="claude-sonnet-4-5-20250929",
        )

        processor = StubDistributedProcessor(
            prepare_result=PrepareResult(state=StubState(), requests=[request]),
            finalise_results=[final_message],
        )

        connector_factory = create_mock_connector_factory(
            "src", [source_schema], source_message
        )
        dispatcher = create_mock_dispatcher([dispatch_result])

        artifacts = {
            "source": ArtifactDefinition(
                source=SourceConfig(type="src", properties={})
            ),
            "findings": ArtifactDefinition(
                inputs="source",
                process=ProcessConfig(type="dist_proc", properties={}),
            ),
        }
        plan = create_simple_plan(
            artifacts,
            {
                "source": (None, source_schema),
                "findings": ([source_schema], output_schema),
            },
        )

        registry = create_mock_registry(
            with_container=True,
            connector_factories={"src": connector_factory},
            processor_factories={
                "dist_proc": create_distributed_processor_factory(
                    "dist_proc", processor
                ),
            },
        )
        registry.get_dispatcher_for.return_value = dispatcher
        executor = DAGExecutor(registry)

        exec_result = await executor.execute(plan)

        store = registry.container.get_service(ArtifactStore)
        stored = await store.get_artifact(exec_result.run_id, "findings")
        assert stored.execution_model_name == "claude-sonnet-4-5-20250929"

    async def test_completed_artifact_deletes_persisted_prepare_result(
        self,
    ) -> None:
        """delete_prepared called on completion.

        Arrange: distributed processor completing via finalise().
        Assert: store.delete_prepared() called for the artifact.
        """
        source_schema = Schema("standard_input", "1.0.0")
        output_schema = Schema("findings", "1.0.0")
        source_message = create_test_message({"files": []})
        final_message = create_test_message(
            {"findings": ["cleanup"]}, schema=output_schema
        )

        request = DispatchRequest(name="cleanup_req")
        dispatch_result = DispatchResult(request_id=request.request_id)

        processor = StubDistributedProcessor(
            prepare_result=PrepareResult(state=StubState(), requests=[request]),
            finalise_results=[final_message],
        )

        connector_factory = create_mock_connector_factory(
            "src", [source_schema], source_message
        )
        dispatcher = create_mock_dispatcher([dispatch_result])

        artifacts = {
            "source": ArtifactDefinition(
                source=SourceConfig(type="src", properties={})
            ),
            "findings": ArtifactDefinition(
                inputs="source",
                process=ProcessConfig(type="dist_proc", properties={}),
            ),
        }
        plan = create_simple_plan(
            artifacts,
            {
                "source": (None, source_schema),
                "findings": ([source_schema], output_schema),
            },
        )

        registry = create_mock_registry(
            with_container=True,
            connector_factories={"src": connector_factory},
            processor_factories={
                "dist_proc": create_distributed_processor_factory(
                    "dist_proc", processor
                ),
            },
        )
        registry.get_dispatcher_for.return_value = dispatcher
        executor = DAGExecutor(registry)

        exec_result = await executor.execute(plan)
        assert "findings" in exec_result.completed

        # Verify prepared state was cleaned up (should not exist)
        store = registry.container.get_service(ArtifactStore)
        assert not await store.prepared_exists(exec_result.run_id, "findings")


# =============================================================================
# Multi-Round
# =============================================================================


class TestMultiRoundDispatch:
    """Tests for multi-round dispatch-finalise cycles."""

    async def test_multi_round_finalise_dispatches_again(self) -> None:
        """finalise() returning PrepareResult triggers another dispatch-finalise cycle.

        Arrange: distributed processor whose finalise() returns a
        PrepareResult on the first call, then a Message on the second.
        Assert: dispatcher.dispatch() called twice (once per round).
        Final artifact content matches the second finalise() Message.
        """
        source_schema = Schema("standard_input", "1.0.0")
        output_schema = Schema("findings", "1.0.0")
        source_message = create_test_message({"files": []})
        final_message = create_test_message(
            {"findings": ["round_2"]}, schema=output_schema
        )

        # Round 1 request/result
        req1 = DispatchRequest(name="round_1")
        res1 = DispatchResult(request_id=req1.request_id)

        # Round 2 request/result
        req2 = DispatchRequest(name="round_2")
        res2 = DispatchResult(request_id=req2.request_id)

        # Processor that needs two rounds
        round2_prepare = PrepareResult(
            state=StubState(value="round_2"), requests=[req2]
        )
        processor = StubDistributedProcessor(
            prepare_result=PrepareResult(
                state=StubState(value="round_1"), requests=[req1]
            ),
            finalise_results=[round2_prepare, final_message],
        )

        connector_factory = create_mock_connector_factory(
            "src", [source_schema], source_message
        )
        # Dispatcher returns the right result for each call
        dispatcher = create_mock_dispatcher([])
        dispatcher.dispatch = AsyncMock(side_effect=[[res1], [res2]])

        artifacts = {
            "source": ArtifactDefinition(
                source=SourceConfig(type="src", properties={})
            ),
            "findings": ArtifactDefinition(
                inputs="source",
                process=ProcessConfig(type="dist_proc", properties={}),
            ),
        }
        plan = create_simple_plan(
            artifacts,
            {
                "source": (None, source_schema),
                "findings": ([source_schema], output_schema),
            },
        )

        registry = create_mock_registry(
            with_container=True,
            connector_factories={"src": connector_factory},
            processor_factories={
                "dist_proc": create_distributed_processor_factory(
                    "dist_proc", processor
                ),
            },
        )
        registry.get_dispatcher_for.return_value = dispatcher
        executor = DAGExecutor(registry)

        exec_result = await executor.execute(plan)

        assert "findings" in exec_result.completed
        assert dispatcher.dispatch.call_count == 2
        assert processor.call_log == ["prepare", "finalise", "finalise"]

        store = registry.container.get_service(ArtifactStore)
        stored = await store.get_artifact(exec_result.run_id, "findings")
        assert stored.content == final_message.content

    async def test_max_rounds_exceeded_fails_artifact(self) -> None:
        """Exceeding max rounds marks the artifact as failed.

        Arrange: distributed processor whose finalise() always returns
        a PrepareResult (never completes).
        Assert: artifact marked failed. Dependents are skipped.
        """
        source_schema = Schema("standard_input", "1.0.0")
        output_schema = Schema("findings", "1.0.0")
        source_message = create_test_message({"files": []})

        # Processor that always returns another PrepareResult.
        # Each round: dispatch req_N → get res_N → finalise returns PrepareResult with req_N+1
        requests = [DispatchRequest(name=f"round_{i}") for i in range(4)]
        results = [DispatchResult(request_id=r.request_id) for r in requests]

        # finalise_results[0] is returned after round 0 dispatch → uses req_1
        # finalise_results[1] is returned after round 1 dispatch → uses req_2
        # finalise_results[2] is returned after round 2 dispatch → uses req_3
        infinite_prepares = [
            PrepareResult(
                state=StubState(value=f"round_{i + 1}"),
                requests=[requests[i + 1]],
            )
            for i in range(3)
        ]
        processor = StubDistributedProcessor(
            prepare_result=PrepareResult(
                state=StubState(value="initial"), requests=[requests[0]]
            ),
            finalise_results=infinite_prepares,
        )

        connector_factory = create_mock_connector_factory(
            "src", [source_schema], source_message
        )
        # Each dispatch call returns the result matching that round's request
        dispatcher = create_mock_dispatcher([])
        dispatcher.dispatch = AsyncMock(side_effect=[[results[i]] for i in range(4)])

        artifacts = {
            "source": ArtifactDefinition(
                source=SourceConfig(type="src", properties={})
            ),
            "findings": ArtifactDefinition(
                inputs="source",
                process=ProcessConfig(type="dist_proc", properties={}),
            ),
            "dependent": ArtifactDefinition(inputs="findings"),
        }
        plan = create_simple_plan(
            artifacts,
            {
                "source": (None, source_schema),
                "findings": ([source_schema], output_schema),
                "dependent": ([output_schema], output_schema),
            },
        )

        registry = create_mock_registry(
            with_container=True,
            connector_factories={"src": connector_factory},
            processor_factories={
                "dist_proc": create_distributed_processor_factory(
                    "dist_proc", processor
                ),
            },
        )
        registry.get_dispatcher_for.return_value = dispatcher
        executor = DAGExecutor(registry)

        exec_result = await executor.execute(plan)

        assert "findings" in exec_result.failed
        assert "dependent" in exec_result.skipped
        # Dispatch called max_rounds times (default 3)
        assert dispatcher.dispatch.call_count == 3
