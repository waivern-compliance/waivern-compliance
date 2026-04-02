"""Tests for distributed processor integration in DAGExecutor.

Verifies end-to-end through execute() that the executor correctly:
- Classifies artifacts and routes distributed processors through prepare-dispatch-finalise
- Groups dispatch requests by type and routes results back
- Handles PendingBatchError and dispatch failures with error isolation
- Resumes pending artifacts from interrupted runs
"""

from pathlib import Path
from typing import override

from waivern_artifact_store import ArtifactStore
from waivern_core import Message
from waivern_core.dispatch import (
    DispatchRequest,
    DispatchResult,
    PrepareResult,
)
from waivern_core.errors import PendingProcessingError
from waivern_core.schemas import Schema

from waivern_orchestration.executor import DAGExecutor
from waivern_orchestration.models import (
    ArtifactDefinition,
    ProcessConfig,
    SourceConfig,
)
from waivern_orchestration.run_metadata import RunMetadata

from .test_helpers import (
    StubDistributedProcessor,
    StubState,
    create_distributed_processor_factory,
    create_mock_connector_factory,
    create_mock_dispatcher,
    create_mock_processor_factory,
    create_mock_registry,
    create_simple_plan,
    create_test_message,
)

# =============================================================================
# Happy Path
# =============================================================================


class TestDistributedProcessorHappyPath:
    """Tests for the distributed processor three-phase lifecycle."""

    async def test_distributed_processor_end_to_end(self) -> None:
        """Source → distributed processor → output with dependent.

        Arrange: source artifact → distributed processor → passthrough dependent.
        Distributed processor's prepare() returns PrepareResult with requests.
        Dispatcher returns matching results. finalise() returns Message.
        Assert: all three artifacts completed. prepare() called (not process()).
        Dependent executes (proving sorter.done was called).
        """
        source_schema = Schema("standard_input", "1.0.0")
        output_schema = Schema("findings", "1.0.0")
        source_message = create_test_message({"files": []})
        final_message = create_test_message(
            {"findings": ["result"]}, schema=output_schema
        )

        # Build dispatch request/result pair
        request = DispatchRequest(name="test_request")
        result = DispatchResult(request_id=request.request_id, name="test_result")

        processor = StubDistributedProcessor(
            prepare_result=PrepareResult(
                state=StubState(value="my_state"),
                requests=[request],
            ),
            finalise_results=[final_message],
        )

        connector_factory = create_mock_connector_factory(
            "filesystem", [source_schema], source_message
        )
        processor_factory = create_distributed_processor_factory(
            "distributed_analyser", processor
        )
        dispatcher = create_mock_dispatcher([result])

        artifacts = {
            "source": ArtifactDefinition(
                source=SourceConfig(type="filesystem", properties={})
            ),
            "findings": ArtifactDefinition(
                inputs="source",
                process=ProcessConfig(type="distributed_analyser", properties={}),
            ),
            "downstream": ArtifactDefinition(inputs="findings"),
        }
        plan = create_simple_plan(
            artifacts,
            {
                "source": (None, source_schema),
                "findings": ([source_schema], output_schema),
                "downstream": ([output_schema], output_schema),
            },
        )

        registry = create_mock_registry(
            with_container=True,
            connector_factories={"filesystem": connector_factory},
            processor_factories={"distributed_analyser": processor_factory},
        )
        registry.get_dispatcher_for.return_value = dispatcher
        executor = DAGExecutor(registry)

        # Act
        exec_result = await executor.execute(plan)

        # Assert — all three completed
        assert {"source", "findings", "downstream"} == exec_result.completed

        # Assert — distributed path used (prepare + finalise, not process)
        assert processor.call_log == ["prepare", "finalise"]

        # Assert — artifact content saved correctly
        store = registry.container.get_service(ArtifactStore)
        findings_msg = await store.get_artifact(exec_result.run_id, "findings")
        assert findings_msg.is_success
        assert findings_msg.content == final_message.content

    async def test_mixed_level_regular_and_distributed_concurrent(self) -> None:
        """Regular processor + distributed processor at same level both complete.

        Arrange: source → two derived artifacts at same level: one regular
        processor, one distributed processor. Both depend on the same source.
        Assert: both derived artifacts completed. Regular used process(),
        distributed used prepare/finalise.
        """
        source_schema = Schema("standard_input", "1.0.0")
        output_schema = Schema("findings", "1.0.0")
        source_message = create_test_message({"files": []})
        regular_result_msg = Message(
            id="regular_out", content={"findings": ["regular"]}, schema=output_schema
        )
        distributed_result_msg = create_test_message(
            {"findings": ["distributed"]}, schema=output_schema
        )

        # Distributed processor setup
        request = DispatchRequest(name="test_req")
        dispatch_result = DispatchResult(request_id=request.request_id, name="test_res")
        dist_processor = StubDistributedProcessor(
            prepare_result=PrepareResult(state=StubState(), requests=[request]),
            finalise_results=[distributed_result_msg],
        )

        connector_factory = create_mock_connector_factory(
            "filesystem", [source_schema], source_message
        )
        regular_factory = create_mock_processor_factory(
            "regular_analyser",
            [source_schema],
            [output_schema],
            process_result=regular_result_msg,
        )
        distributed_factory = create_distributed_processor_factory(
            "distributed_analyser", dist_processor
        )
        dispatcher = create_mock_dispatcher([dispatch_result])

        artifacts = {
            "source": ArtifactDefinition(
                source=SourceConfig(type="filesystem", properties={})
            ),
            "regular_findings": ArtifactDefinition(
                inputs="source",
                process=ProcessConfig(type="regular_analyser", properties={}),
            ),
            "distributed_findings": ArtifactDefinition(
                inputs="source",
                process=ProcessConfig(type="distributed_analyser", properties={}),
            ),
        }
        plan = create_simple_plan(
            artifacts,
            {
                "source": (None, source_schema),
                "regular_findings": ([source_schema], output_schema),
                "distributed_findings": ([source_schema], output_schema),
            },
        )

        registry = create_mock_registry(
            with_container=True,
            connector_factories={"filesystem": connector_factory},
            processor_factories={
                "regular_analyser": regular_factory,
                "distributed_analyser": distributed_factory,
            },
        )
        registry.get_dispatcher_for.return_value = dispatcher
        executor = DAGExecutor(registry)

        # Act
        exec_result = await executor.execute(plan)

        # Assert — all three completed
        assert {
            "source",
            "regular_findings",
            "distributed_findings",
        } == exec_result.completed

        # Assert — correct code paths used
        assert dist_processor.call_log == ["prepare", "finalise"]
        regular_factory.create.return_value.process.assert_called_once()


# =============================================================================
# Dispatch
# =============================================================================


class TestDistributedDispatch:
    """Tests for dispatch grouping, routing, and error handling."""

    async def test_requests_grouped_by_type_and_dispatched(self) -> None:
        """Requests from multiple artifacts of the same type are grouped.

        Arrange: two distributed processors at the same level, both
        producing requests of the same DispatchRequest subclass.
        Assert: dispatcher.dispatch() called once with all requests
        combined, not once per artifact.
        """
        source_schema = Schema("standard_input", "1.0.0")
        output_schema = Schema("findings", "1.0.0")
        source_message = create_test_message({"files": []})
        final_message = create_test_message(
            {"findings": ["done"]}, schema=output_schema
        )

        # Two processors, each with one request
        req_a = DispatchRequest(name="req_a")
        req_b = DispatchRequest(name="req_b")
        res_a = DispatchResult(request_id=req_a.request_id)
        res_b = DispatchResult(request_id=req_b.request_id)

        proc_a = StubDistributedProcessor(
            prepare_result=PrepareResult(state=StubState(), requests=[req_a]),
            finalise_results=[final_message],
        )
        proc_b = StubDistributedProcessor(
            prepare_result=PrepareResult(state=StubState(), requests=[req_b]),
            finalise_results=[final_message],
        )

        connector_factory = create_mock_connector_factory(
            "src", [source_schema], source_message
        )
        dispatcher = create_mock_dispatcher([res_a, res_b])

        artifacts = {
            "source": ArtifactDefinition(
                source=SourceConfig(type="src", properties={})
            ),
            "a": ArtifactDefinition(
                inputs="source",
                process=ProcessConfig(type="proc_a", properties={}),
            ),
            "b": ArtifactDefinition(
                inputs="source",
                process=ProcessConfig(type="proc_b", properties={}),
            ),
        }
        plan = create_simple_plan(
            artifacts,
            {
                "source": (None, source_schema),
                "a": ([source_schema], output_schema),
                "b": ([source_schema], output_schema),
            },
        )

        registry = create_mock_registry(
            with_container=True,
            connector_factories={"src": connector_factory},
            processor_factories={
                "proc_a": create_distributed_processor_factory("proc_a", proc_a),
                "proc_b": create_distributed_processor_factory("proc_b", proc_b),
            },
        )
        registry.get_dispatcher_for.return_value = dispatcher
        executor = DAGExecutor(registry)

        exec_result = await executor.execute(plan)

        assert {"source", "a", "b"} == exec_result.completed
        # dispatch() called once with both requests grouped
        dispatcher.dispatch.assert_called_once()
        dispatched_requests = dispatcher.dispatch.call_args[0][0]
        assert len(dispatched_requests) == 2

    async def test_results_routed_back_to_correct_artifacts(self) -> None:
        """Dispatch results are routed to the correct artifact via request_id.

        Arrange: two distributed processors each producing requests with
        distinct request_ids. Dispatcher returns results with matching ids.
        Assert: each processor's finalise() receives only its own results.
        """
        source_schema = Schema("standard_input", "1.0.0")
        output_schema = Schema("findings", "1.0.0")
        source_message = create_test_message({"files": []})

        req_a = DispatchRequest(name="req_a")
        req_b = DispatchRequest(name="req_b")
        res_a = DispatchResult(request_id=req_a.request_id, name="result_for_a")
        res_b = DispatchResult(request_id=req_b.request_id, name="result_for_b")

        # Track what each finalise receives
        finalise_args: dict[str, list[DispatchResult]] = {}

        class TrackingProcessor(StubDistributedProcessor):
            def __init__(
                self,
                tag: str,
                prepare_result: PrepareResult[StubState],
                final_msg: Message,
            ) -> None:
                super().__init__(prepare_result, [final_msg])
                self.tag = tag

            def finalise(self, state, results, output_schema):  # type: ignore[override]
                finalise_args[self.tag] = list(results)
                return super().finalise(state, results, output_schema)

        final_msg = create_test_message({"findings": []}, schema=output_schema)
        proc_a = TrackingProcessor(
            "a", PrepareResult(state=StubState(), requests=[req_a]), final_msg
        )
        proc_b = TrackingProcessor(
            "b", PrepareResult(state=StubState(), requests=[req_b]), final_msg
        )

        connector_factory = create_mock_connector_factory(
            "src", [source_schema], source_message
        )
        dispatcher = create_mock_dispatcher([res_a, res_b])

        artifacts = {
            "source": ArtifactDefinition(
                source=SourceConfig(type="src", properties={})
            ),
            "a": ArtifactDefinition(
                inputs="source",
                process=ProcessConfig(type="proc_a", properties={}),
            ),
            "b": ArtifactDefinition(
                inputs="source",
                process=ProcessConfig(type="proc_b", properties={}),
            ),
        }
        plan = create_simple_plan(
            artifacts,
            {
                "source": (None, source_schema),
                "a": ([source_schema], output_schema),
                "b": ([source_schema], output_schema),
            },
        )

        registry = create_mock_registry(
            with_container=True,
            connector_factories={"src": connector_factory},
            processor_factories={
                "proc_a": create_distributed_processor_factory("proc_a", proc_a),
                "proc_b": create_distributed_processor_factory("proc_b", proc_b),
            },
        )
        registry.get_dispatcher_for.return_value = dispatcher
        executor = DAGExecutor(registry)

        exec_result = await executor.execute(plan)

        assert {"source", "a", "b"} == exec_result.completed
        # Each processor got only its own result
        assert len(finalise_args["a"]) == 1
        assert finalise_args["a"][0].name == "result_for_a"
        assert len(finalise_args["b"]) == 1
        assert finalise_args["b"][0].name == "result_for_b"

    async def test_pending_batch_error_persists_and_marks_pending(self) -> None:
        """PendingBatchError persists PrepareResult and marks artifacts pending.

        Arrange: dispatcher raises PendingProcessingError (PendingBatchError).
        Assert:
        - PrepareResult saved to store via save_prepared()
        - Artifact marked pending in ExecutionState
        - Run status is "interrupted" (not failed)
        - Artifact NOT in completed, failed, or skipped
        """
        source_schema = Schema("standard_input", "1.0.0")
        output_schema = Schema("findings", "1.0.0")
        source_message = create_test_message({"files": []})

        request = DispatchRequest(name="pending_req")
        processor = StubDistributedProcessor(
            prepare_result=PrepareResult(
                state=StubState(value="pending_state"),
                requests=[request],
            ),
            finalise_results=[create_test_message({}, schema=output_schema)],
        )

        connector_factory = create_mock_connector_factory(
            "src", [source_schema], source_message
        )
        dispatcher = create_mock_dispatcher(
            [], side_effect=PendingProcessingError("Batch pending")
        )

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

        # Artifact not in completed, failed, or skipped
        assert "findings" not in exec_result.completed
        assert "findings" not in exec_result.failed
        assert "findings" not in exec_result.skipped
        assert "source" in exec_result.completed

        # Run status is interrupted
        store = registry.container.get_service(ArtifactStore)
        metadata = await RunMetadata.load(store, exec_result.run_id)
        assert metadata.status == "interrupted"

        # PrepareResult was persisted
        raw = await store.load_prepared(exec_result.run_id, "findings")
        assert raw["state"]["value"] == "pending_state"

    async def test_dispatch_error_fails_distributed_regular_unaffected(self) -> None:
        """Dispatch error fails distributed artifacts; regular at same level unaffected.

        Arrange: source → regular processor + distributed processor at same level.
        Dispatcher raises RuntimeError.
        Assert: distributed artifact failed, regular artifact completed.
        """
        source_schema = Schema("standard_input", "1.0.0")
        output_schema = Schema("findings", "1.0.0")
        source_message = create_test_message({"files": []})
        regular_result = Message(
            id="regular", content={"findings": []}, schema=output_schema
        )

        request = DispatchRequest(name="failing_req")
        dist_processor = StubDistributedProcessor(
            prepare_result=PrepareResult(state=StubState(), requests=[request]),
            finalise_results=[create_test_message({}, schema=output_schema)],
        )

        connector_factory = create_mock_connector_factory(
            "src", [source_schema], source_message
        )
        regular_factory = create_mock_processor_factory(
            "regular", [source_schema], [output_schema], process_result=regular_result
        )
        dispatcher = create_mock_dispatcher(
            [], side_effect=RuntimeError("Dispatch failed")
        )

        artifacts = {
            "source": ArtifactDefinition(
                source=SourceConfig(type="src", properties={})
            ),
            "regular_out": ArtifactDefinition(
                inputs="source",
                process=ProcessConfig(type="regular", properties={}),
            ),
            "distributed_out": ArtifactDefinition(
                inputs="source",
                process=ProcessConfig(type="dist_proc", properties={}),
            ),
        }
        plan = create_simple_plan(
            artifacts,
            {
                "source": (None, source_schema),
                "regular_out": ([source_schema], output_schema),
                "distributed_out": ([source_schema], output_schema),
            },
        )

        registry = create_mock_registry(
            with_container=True,
            connector_factories={"src": connector_factory},
            processor_factories={
                "regular": regular_factory,
                "dist_proc": create_distributed_processor_factory(
                    "dist_proc", dist_processor
                ),
            },
        )
        registry.get_dispatcher_for.return_value = dispatcher
        executor = DAGExecutor(registry)

        exec_result = await executor.execute(plan)

        assert {"source", "regular_out"} == exec_result.completed
        assert "distributed_out" in exec_result.failed

    async def test_short_circuited_entries_get_empty_results(self) -> None:
        """Entries with empty requests skip dispatch and get empty results.

        Arrange: distributed processor whose prepare() returns a
        PrepareResult with empty requests list.
        Assert: artifact completed. finalise() called with empty results.
        No dispatcher resolved or called.
        """
        source_schema = Schema("standard_input", "1.0.0")
        output_schema = Schema("findings", "1.0.0")
        source_message = create_test_message({"files": []})
        final_message = create_test_message(
            {"findings": ["short_circuit"]}, schema=output_schema
        )

        processor = StubDistributedProcessor(
            prepare_result=PrepareResult(state=StubState(), requests=[]),
            finalise_results=[final_message],
        )

        connector_factory = create_mock_connector_factory(
            "src", [source_schema], source_message
        )

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
        executor = DAGExecutor(registry)

        exec_result = await executor.execute(plan)

        assert {"source", "findings"} == exec_result.completed
        assert processor.call_log == ["prepare", "finalise"]
        # No dispatcher was needed
        registry.get_dispatcher_for.assert_not_called()


# =============================================================================
# Error Isolation
# =============================================================================


class TestDistributedErrorIsolation:
    """Tests for error isolation between regular and distributed paths."""

    async def test_prepare_failure_fails_artifact_regular_unaffected(self) -> None:
        """prepare() throwing fails only that artifact; regular at same level unaffected.

        Arrange: source → regular processor + distributed processor at same level.
        Distributed processor's prepare() raises RuntimeError.
        Assert: distributed artifact failed with dependents skipped.
        Regular artifact completed normally.
        """
        source_schema = Schema("standard_input", "1.0.0")
        output_schema = Schema("findings", "1.0.0")
        source_message = create_test_message({"files": []})
        regular_result = Message(
            id="ok", content={"findings": []}, schema=output_schema
        )

        # Processor whose prepare() raises
        class FailingPrepareProcessor(StubDistributedProcessor):
            @override
            def prepare(self, inputs, output_schema):  # type: ignore[override]
                raise RuntimeError("prepare failed")

        failing_processor = FailingPrepareProcessor(
            prepare_result=PrepareResult(state=StubState(), requests=[]),
            finalise_results=[create_test_message({}, schema=output_schema)],
        )

        connector_factory = create_mock_connector_factory(
            "src", [source_schema], source_message
        )
        regular_factory = create_mock_processor_factory(
            "regular", [source_schema], [output_schema], process_result=regular_result
        )

        artifacts = {
            "source": ArtifactDefinition(
                source=SourceConfig(type="src", properties={})
            ),
            "regular_out": ArtifactDefinition(
                inputs="source",
                process=ProcessConfig(type="regular", properties={}),
            ),
            "distributed_out": ArtifactDefinition(
                inputs="source",
                process=ProcessConfig(type="dist_proc", properties={}),
            ),
            "dependent": ArtifactDefinition(inputs="distributed_out"),
        }
        plan = create_simple_plan(
            artifacts,
            {
                "source": (None, source_schema),
                "regular_out": ([source_schema], output_schema),
                "distributed_out": ([source_schema], output_schema),
                "dependent": ([output_schema], output_schema),
            },
        )

        registry = create_mock_registry(
            with_container=True,
            connector_factories={"src": connector_factory},
            processor_factories={
                "regular": regular_factory,
                "dist_proc": create_distributed_processor_factory(
                    "dist_proc", failing_processor
                ),
            },
        )
        executor = DAGExecutor(registry)

        exec_result = await executor.execute(plan)

        assert {"source", "regular_out"} == exec_result.completed
        assert "distributed_out" in exec_result.failed
        assert "dependent" in exec_result.skipped


# =============================================================================
# Resume
# =============================================================================


class TestDistributedResume:
    """Tests for resuming interrupted runs with pending distributed artifacts."""

    async def test_resume_pending_artifact_skips_prepare(self, tmp_path: Path) -> None:
        """Pending artifact from interrupted run skips prepare, dispatches, completes.

        Arrange: first run — distributed processor, dispatcher raises
        PendingProcessingError → artifact pending, run interrupted.
        Second run (resume) — dispatcher succeeds.
        Assert: prepare() called once (first run only). deserialise_prepare_result()
        called on resume. finalise() produces Message → artifact completed.
        """
        source_schema = Schema("standard_input", "1.0.0")
        output_schema = Schema("findings", "1.0.0")
        source_message = create_test_message({"files": []})
        final_message = create_test_message(
            {"findings": ["resumed"]}, schema=output_schema
        )

        request = DispatchRequest(name="resume_req")
        dispatch_result = DispatchResult(request_id=request.request_id)

        processor = StubDistributedProcessor(
            prepare_result=PrepareResult(
                state=StubState(value="resume_state"),
                requests=[request],
            ),
            finalise_results=[final_message],
        )

        connector_factory = create_mock_connector_factory(
            "src", [source_schema], source_message
        )
        processor_factory = create_distributed_processor_factory("dist_proc", processor)

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

        runbook_file = tmp_path / "runbook.yaml"
        runbook_file.write_text("name: test\ndescription: test\n")

        # First run — dispatcher raises PendingProcessingError
        pending_dispatcher = create_mock_dispatcher(
            [], side_effect=PendingProcessingError("Batch pending")
        )
        registry = create_mock_registry(
            with_container=True,
            connector_factories={"src": connector_factory},
            processor_factories={"dist_proc": processor_factory},
        )
        registry.get_dispatcher_for.return_value = pending_dispatcher
        executor = DAGExecutor(registry)

        result1 = await executor.execute(plan, runbook_path=runbook_file)
        assert "findings" not in result1.completed
        assert "source" in result1.completed

        # Second run (resume) — dispatcher succeeds
        ok_dispatcher = create_mock_dispatcher([dispatch_result])
        registry.get_dispatcher_for.return_value = ok_dispatcher

        # Re-create processor to track second-run calls separately
        processor2 = StubDistributedProcessor(
            prepare_result=PrepareResult(
                state=StubState(value="resume_state"),
                requests=[request],
            ),
            finalise_results=[final_message],
        )
        processor_factory2 = create_distributed_processor_factory(
            "dist_proc", processor2
        )
        registry.processor_factories["dist_proc"] = processor_factory2

        result2 = await executor.execute(
            plan, runbook_path=runbook_file, resume_run_id=result1.run_id
        )

        # Assert — artifact completed on resume
        assert "findings" in result2.completed

        # Assert — prepare NOT called on resume (only deserialise + finalise)
        assert "prepare" not in processor2.call_log
        assert "deserialise_prepare_result" in processor2.call_log
        assert "finalise" in processor2.call_log
