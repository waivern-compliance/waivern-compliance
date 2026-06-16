"""Tests for sidecar persistence and back-reference stamping in DAGExecutor.

Covers both code paths (sync ``_run_processor`` and distributed
``_finalise_distributed_artifacts``) and the audit-trail back-reference
stamping into the primary's ``analysis_metadata.validation_summary``.
"""

from collections.abc import Sequence
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from waivern_artifact_store import ArtifactStore
from waivern_core import (
    LLMValidationResponseModel,
    LLMValidationResultModel,
    Message,
)
from waivern_core.dispatch import DispatchRequest, DispatchResult, PrepareResult
from waivern_core.schemas import Schema
from waivern_llm.types import LLMDispatchResult, LLMRequest

from waivern_orchestration.executor import DAGExecutor
from waivern_orchestration.models import (
    ArtifactDefinition,
    ProcessConfig,
    SourceConfig,
)
from waivern_orchestration.planner import ExecutionPlan

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


def _build_sync_plan_and_registry(
    primary: Message,
    sidecars: list[Message],
    output_schema: Schema,
) -> tuple[ExecutionPlan, MagicMock]:
    """Build a minimal plan + registry for a single synchronous-processor artifact.

    Source connector → regular ``Processor.process()`` returning
    ``(primary, sidecars)``.
    """
    source_schema = Schema("standard_input", "1.0.0")
    source_message = create_test_message({"files": []})

    connector_factory = create_mock_connector_factory(
        "src", [source_schema], source_message
    )
    processor_factory = create_mock_processor_factory(
        "sync_proc",
        input_schemas=[source_schema],
        output_schemas=[output_schema],
        process_result=(primary, sidecars),
    )

    artifacts = {
        "source": ArtifactDefinition(source=SourceConfig(type="src", properties={})),
        "findings": ArtifactDefinition(
            inputs="source",
            process=ProcessConfig(type="sync_proc", properties={}),
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
        processor_factories={"sync_proc": processor_factory},
    )
    return plan, registry


def _build_distributed_plan_and_registry(
    primary: Message,
    sidecars: list[Message],
    output_schema: Schema,
) -> tuple[ExecutionPlan, MagicMock]:
    """Build a minimal plan + registry for a single distributed-processor artifact.

    Single source connector feeding a single distributed processor that
    returns ``(primary, sidecars)`` in one round.
    """
    source_schema = Schema("standard_input", "1.0.0")
    source_message = create_test_message({"files": []})

    request = DispatchRequest(name="req")
    dispatch_result = DispatchResult(request_id=request.request_id)

    processor = StubDistributedProcessor(
        prepare_result=PrepareResult(state=StubState(), requests=[request]),
        finalise_results=[(primary, sidecars)],
    )

    connector_factory = create_mock_connector_factory(
        "src", [source_schema], source_message
    )
    dispatcher = create_mock_dispatcher([dispatch_result])

    artifacts = {
        "source": ArtifactDefinition(source=SourceConfig(type="src", properties={})),
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
            "dist_proc": create_distributed_processor_factory("dist_proc", processor),
        },
    )
    registry.get_dispatcher_for.return_value = dispatcher
    return plan, registry


class TestDistributedSidecarPersistence:
    """Group A — sidecar persistence on the distributed (DistributedProcessor) path."""

    async def test_distributed_sidecar_persisted_at_dotted_artifact_id(self) -> None:
        """Distributed (primary, [sidecar]) → sidecar in store at ``{primary}.{schema.name}``.

        Arrange: distributed processor finalises with one ``removed_findings``
        sidecar alongside the primary.
        Assert: ``store.get_artifact(run_id, "findings.removed_findings")``
        returns a Message whose schema matches the sidecar's schema.
        """
        output_schema = Schema("findings", "1.0.0")
        sidecar_schema = Schema("removed_findings", "1.0.0")

        primary = create_test_message({"findings": []}, schema=output_schema)
        sidecar = create_test_message(
            {"analyser_name": "x", "run_id": "x", "removed_findings": []},
            schema=sidecar_schema,
        )

        plan, registry = _build_distributed_plan_and_registry(
            primary, [sidecar], output_schema
        )
        executor = DAGExecutor(registry)

        exec_result = await executor.execute(plan)
        assert "findings" in exec_result.completed

        store = registry.container.get_service(ArtifactStore)
        stored = await store.get_artifact(
            exec_result.run_id, "findings.removed_findings"
        )
        assert stored.schema == sidecar_schema

    async def test_distributed_sidecar_carries_run_id(self) -> None:
        """Persisted sidecar carries the executor's run_id, not whatever the analyser set.

        The store is queried by (run_id, artifact_id); a sidecar with the
        wrong (or missing) run_id is unreachable.
        """
        output_schema = Schema("findings", "1.0.0")
        sidecar_schema = Schema("removed_findings", "1.0.0")

        primary = create_test_message({"findings": []}, schema=output_schema)
        sidecar = create_test_message(
            {"analyser_name": "x", "run_id": "stale-id", "removed_findings": []},
            schema=sidecar_schema,
        )

        plan, registry = _build_distributed_plan_and_registry(
            primary, [sidecar], output_schema
        )
        executor = DAGExecutor(registry)

        exec_result = await executor.execute(plan)

        store = registry.container.get_service(ArtifactStore)
        stored = await store.get_artifact(
            exec_result.run_id, "findings.removed_findings"
        )
        assert stored.run_id == exec_result.run_id

    async def test_distributed_multiple_sidecars_all_persisted(self) -> None:
        """Two sidecars with different schema.name → both land at their dotted IDs.

        Forward-compat: defends the iteration loop against off-by-one or
        "save only first" regressions as future sidecar types arrive.
        """
        output_schema = Schema("findings", "1.0.0")
        sidecar_a_schema = Schema("removed_findings", "1.0.0")
        sidecar_b_schema = Schema("standard_input", "1.0.0")

        primary = create_test_message({"findings": []}, schema=output_schema)
        sidecar_a = create_test_message({"a": 1}, schema=sidecar_a_schema)
        sidecar_b = create_test_message({"b": 2}, schema=sidecar_b_schema)

        plan, registry = _build_distributed_plan_and_registry(
            primary, [sidecar_a, sidecar_b], output_schema
        )
        executor = DAGExecutor(registry)

        exec_result = await executor.execute(plan)

        store = registry.container.get_service(ArtifactStore)
        stored_a = await store.get_artifact(
            exec_result.run_id, "findings.removed_findings"
        )
        stored_b = await store.get_artifact(
            exec_result.run_id, "findings.standard_input"
        )
        assert stored_a.schema == sidecar_a_schema
        assert stored_b.schema == sidecar_b_schema

    async def test_distributed_no_sidecars_stores_only_primary(self) -> None:
        """Empty sidecar list → only the primary is in the store (no spurious files).

        Negative case for the persistence loop.
        """
        output_schema = Schema("findings", "1.0.0")
        primary = create_test_message({"findings": []}, schema=output_schema)

        plan, registry = _build_distributed_plan_and_registry(
            primary, [], output_schema
        )
        executor = DAGExecutor(registry)

        exec_result = await executor.execute(plan)

        store = registry.container.get_service(ArtifactStore)
        artifact_ids = await store.list_artifacts(exec_result.run_id)
        # Only the source and the primary "findings" — no sidecars.
        assert sorted(artifact_ids) == ["findings", "source"]


class TestSyncSidecarPersistence:
    """Group B — sidecar persistence on the synchronous (Processor.process) path."""

    async def test_sync_sidecar_persisted_at_dotted_artifact_id(self) -> None:
        """Sync ``Processor.process()`` returning ``(primary, [sidecar])`` persists both.

        Arrange: a regular (non-DistributedProcessor) processor that returns
        a primary plus one sidecar.
        Assert: store has the sidecar at ``{primary}.{schema.name}``.
        """
        output_schema = Schema("findings", "1.0.0")
        sidecar_schema = Schema("removed_findings", "1.0.0")

        primary = create_test_message({"findings": []}, schema=output_schema)
        sidecar = create_test_message(
            {"analyser_name": "x", "run_id": "x", "removed_findings": []},
            schema=sidecar_schema,
        )

        plan, registry = _build_sync_plan_and_registry(
            primary, [sidecar], output_schema
        )
        executor = DAGExecutor(registry)

        exec_result = await executor.execute(plan)
        assert "findings" in exec_result.completed

        store = registry.container.get_service(ArtifactStore)
        stored = await store.get_artifact(
            exec_result.run_id, "findings.removed_findings"
        )
        assert stored.schema == sidecar_schema
        assert stored.run_id == exec_result.run_id

    async def test_sync_no_sidecars_stores_only_primary(self) -> None:
        """Sync processor returning ``(primary, [])`` → only primary in store.

        Negative case mirroring A4 on the synchronous path.
        """
        output_schema = Schema("findings", "1.0.0")
        primary = create_test_message({"findings": []}, schema=output_schema)

        plan, registry = _build_sync_plan_and_registry(primary, [], output_schema)
        executor = DAGExecutor(registry)

        exec_result = await executor.execute(plan)

        store = registry.container.get_service(ArtifactStore)
        artifact_ids = await store.list_artifacts(exec_result.run_id)
        assert sorted(artifact_ids) == ["findings", "source"]


class TestBackReferenceStamping:
    """Group C — stamping ``removed_findings_artifact_id`` into the primary."""

    async def test_removed_findings_sidecar_stamps_artifact_id_into_validation_summary(
        self,
    ) -> None:
        """``removed_findings`` sidecar → primary's ``validation_summary`` carries back-ref.

        The bridge between the primary output and the audit-trail sidecar:
        downstream consumers reading the primary find the sidecar's
        artifact_id under
        ``analysis_metadata.validation_summary.removed_findings_artifact_id``.
        """
        output_schema = Schema("findings", "1.0.0")
        sidecar_schema = Schema("removed_findings", "1.0.0")

        primary = create_test_message(
            {
                "findings": [],
                "analysis_metadata": {
                    "validation_summary": {
                        "removed_findings_artifact_id": None,
                    },
                },
            },
            schema=output_schema,
        )
        sidecar = create_test_message(
            {"analyser_name": "x", "run_id": "x", "removed_findings": []},
            schema=sidecar_schema,
        )

        plan, registry = _build_distributed_plan_and_registry(
            primary, [sidecar], output_schema
        )
        executor = DAGExecutor(registry)

        exec_result = await executor.execute(plan)

        store = registry.container.get_service(ArtifactStore)
        stored_primary = await store.get_artifact(exec_result.run_id, "findings")
        validation_summary = stored_primary.content["analysis_metadata"][
            "validation_summary"
        ]
        assert (
            validation_summary["removed_findings_artifact_id"]
            == "findings.removed_findings"
        )

    async def test_non_removed_findings_sidecar_does_not_stamp(self) -> None:
        """A sidecar with a different schema.name does not trigger stamping.

        Locks in the matching rule: only ``removed_findings`` sidecars
        cause back-reference stamping. Future sidecar types (e.g. SOC 2
        evidence trail) are persisted but do not back-stamp.
        """
        output_schema = Schema("findings", "1.0.0")
        sidecar_schema = Schema("some_other_sidecar", "1.0.0")

        primary = create_test_message(
            {
                "findings": [],
                "analysis_metadata": {
                    "validation_summary": {
                        "removed_findings_artifact_id": None,
                    },
                },
            },
            schema=output_schema,
        )
        sidecar = create_test_message({"x": 1}, schema=sidecar_schema)

        plan, registry = _build_distributed_plan_and_registry(
            primary, [sidecar], output_schema
        )
        executor = DAGExecutor(registry)

        exec_result = await executor.execute(plan)

        store = registry.container.get_service(ArtifactStore)
        stored_primary = await store.get_artifact(exec_result.run_id, "findings")
        validation_summary = stored_primary.content["analysis_metadata"][
            "validation_summary"
        ]
        # Untouched — still the pre-emitted None.
        assert validation_summary["removed_findings_artifact_id"] is None

    async def test_primary_without_validation_summary_skips_stamp_gracefully(
        self,
    ) -> None:
        """Primary lacking ``analysis_metadata.validation_summary`` is untouched.

        Defensive: a non-analyser processor (e.g. raw passthrough) that
        somehow emits a ``removed_findings`` sidecar must not cause the
        executor to crash. The sidecar persists; the primary stays as-is.
        """
        output_schema = Schema("findings", "1.0.0")
        sidecar_schema = Schema("removed_findings", "1.0.0")

        primary = create_test_message({"findings": []}, schema=output_schema)
        sidecar = create_test_message(
            {"analyser_name": "x", "run_id": "x", "removed_findings": []},
            schema=sidecar_schema,
        )

        plan, registry = _build_distributed_plan_and_registry(
            primary, [sidecar], output_schema
        )
        executor = DAGExecutor(registry)

        exec_result = await executor.execute(plan)

        store = registry.container.get_service(ArtifactStore)
        stored_primary = await store.get_artifact(exec_result.run_id, "findings")
        # Primary content unchanged (no analysis_metadata fabricated by executor).
        assert "analysis_metadata" not in stored_primary.content
        # Sidecar still persisted.
        assert await store.artifact_exists(
            exec_result.run_id, "findings.removed_findings"
        )

    async def test_validation_with_no_removals_no_sidecar_no_stamp(self) -> None:
        """Validation produced no removals → no sidecar → primary unchanged.

        Common case: LLM validation enabled, but no false positives found.
        The analyser pre-emits ``removed_findings_artifact_id: None`` in
        ``validation_summary``; the executor sees no sidecar and leaves
        that ``None`` in place.
        """
        output_schema = Schema("findings", "1.0.0")
        primary = create_test_message(
            {
                "findings": [],
                "analysis_metadata": {
                    "validation_summary": {
                        "removed_findings_artifact_id": None,
                    },
                },
            },
            schema=output_schema,
        )

        plan, registry = _build_distributed_plan_and_registry(
            primary, [], output_schema
        )
        executor = DAGExecutor(registry)

        exec_result = await executor.execute(plan)

        store = registry.container.get_service(ArtifactStore)
        stored_primary = await store.get_artifact(exec_result.run_id, "findings")
        validation_summary = stored_primary.content["analysis_metadata"][
            "validation_summary"
        ]
        assert validation_summary["removed_findings_artifact_id"] is None


class TestSidecarSaveOrder:
    """Group D — sidecars must be persisted before the primary (crash safety)."""

    async def test_sidecars_saved_before_primary(self, mocker: MockerFixture) -> None:
        """Sidecars are saved before the primary.

        Crash safety invariant: if execution crashes after a sidecar write
        but before the primary write, the artifact is not marked completed,
        so resume re-runs it idempotently. Reversing the order would risk
        the primary's stamped ``removed_findings_artifact_id`` pointing at
        a sidecar that was never persisted.
        """
        output_schema = Schema("findings", "1.0.0")
        sidecar_schema = Schema("removed_findings", "1.0.0")

        primary = create_test_message({"findings": []}, schema=output_schema)
        sidecar = create_test_message(
            {"analyser_name": "x", "run_id": "x", "removed_findings": []},
            schema=sidecar_schema,
        )

        plan, registry = _build_distributed_plan_and_registry(
            primary, [sidecar], output_schema
        )
        store = registry.container.get_service(ArtifactStore)
        spy = mocker.spy(store, "save_artifact")

        executor = DAGExecutor(registry)
        await executor.execute(plan)

        # save_artifact is called for: source (connector output), then
        # findings.removed_findings (sidecar), then findings (primary).
        # We assert the sidecar precedes the primary for the same artifact.
        saved_ids = [call.args[1] for call in spy.call_args_list]
        sidecar_idx = saved_ids.index("findings.removed_findings")
        primary_idx = saved_ids.index("findings")
        assert sidecar_idx < primary_idx


class _AllFalsePositiveDispatcher:
    """Test dispatcher that marks every finding in every request FALSE_POSITIVE."""

    async def dispatch(
        self, requests: Sequence[DispatchRequest]
    ) -> Sequence[DispatchResult]:
        results: list[DispatchResult] = []
        for request in requests:
            assert isinstance(request, LLMRequest)
            verdict_results = [
                LLMValidationResultModel(
                    finding_id=item.id,
                    validation_result="FALSE_POSITIVE",
                    confidence=0.9,
                    reasoning="LLM rejected: not actually personal data",
                    recommended_action="discard",
                )
                for group in request.groups
                for item in group.items
            ]
            response = LLMValidationResponseModel(results=verdict_results)
            results.append(
                LLMDispatchResult(
                    request_id=request.request_id,
                    model_name="test-model",
                    responses=[response.model_dump(mode="json")],
                    skipped=[],
                )
            )
        return results


class TestAnalyserSidecarE2E:
    """Group E — end-to-end through a real LLM-validating analyser."""

    async def test_personal_data_analyser_audit_trail_e2e(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """personal_data_analyser through executor → sidecar persisted + back-ref stamped.

        Integration smoke validating that the real analyser's primary
        content shape matches the executor's stamping path. Uses synthetic
        ruleset rules to avoid coupling to production ruleset data.
        """
        from waivern_analysers_shared.types import (
            LLMValidationConfig,
            PatternMatchingConfig,
        )
        from waivern_analysers_shared.utilities import RulesetManager
        from waivern_personal_data_analyser.analyser import PersonalDataAnalyser
        from waivern_personal_data_analyser.types import PersonalDataAnalyserConfig
        from waivern_rulesets.personal_data_indicator import (
            PersonalDataIndicatorRule,
        )
        from waivern_schemas import register_schemas
        from waivern_schemas.connector_types import BaseMetadata
        from waivern_schemas.standard_input import (
            StandardInputDataItemModel,
            StandardInputDataModel,
        )

        # Make personal_data_indicator JSON schema discoverable; the
        # workspace conftest snapshots/restores SchemaRegistry per test.
        register_schemas()

        synthetic_rules = (
            PersonalDataIndicatorRule(
                name="Email Address",
                description="Email detection",
                category="email",
                patterns=("email",),
            ),
        )

        def _mock_get_rules(
            uri: str, rule_type: type[PersonalDataIndicatorRule]
        ) -> tuple[PersonalDataIndicatorRule, ...]:
            return synthetic_rules

        monkeypatch.setattr(RulesetManager, "get_rules", _mock_get_rules)

        config = PersonalDataAnalyserConfig(
            pattern_matching=PatternMatchingConfig(ruleset="test/personal_data/1.0.0"),
            llm_validation=LLMValidationConfig(
                enable_llm_validation=True,
                llm_validation_mode="standard",
            ),
        )
        analyser = PersonalDataAnalyser(config=config)

        source_schema = Schema("standard_input", "1.0.0")
        output_schema = Schema("personal_data_indicator", "1.0.0")
        input_data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="test_data",
            data=[
                StandardInputDataItemModel(
                    content="Contact email: john.doe@company.com",
                    metadata=BaseMetadata(source="email_source", connector_type="test"),
                ),
            ],
        )
        source_message = Message(
            id="src-msg",
            content=input_data.model_dump(exclude_none=True),
            schema=source_schema,
        )

        connector_factory = create_mock_connector_factory(
            "src", [source_schema], source_message
        )
        # Inline a factory matching ``create_distributed_processor_factory`` but
        # accepting any DistributedProcessor, since the shared helper is typed
        # to a stub class.
        analyser_factory = MagicMock()
        analyser_factory.component_class = MagicMock()
        analyser_factory.component_class.get_name.return_value = "pda"
        analyser_factory.create.return_value = analyser

        artifacts = {
            "source": ArtifactDefinition(
                source=SourceConfig(type="src", properties={})
            ),
            "findings": ArtifactDefinition(
                inputs="source",
                process=ProcessConfig(type="pda", properties={}),
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
            processor_factories={"pda": analyser_factory},
        )
        registry.get_dispatcher_for.return_value = _AllFalsePositiveDispatcher()

        executor = DAGExecutor(registry)
        exec_result = await executor.execute(plan)
        assert "findings" in exec_result.completed, exec_result.failed

        store = registry.container.get_service(ArtifactStore)
        stored_primary = await store.get_artifact(exec_result.run_id, "findings")
        stored_sidecar = await store.get_artifact(
            exec_result.run_id, "findings.removed_findings"
        )

        # Sidecar carries the analyser's audit trail with the LLM's reasoning verbatim.
        assert stored_sidecar.schema == Schema("removed_findings", "1.0.0")
        removed = stored_sidecar.content["removed_findings"]
        assert len(removed) >= 1
        assert all(
            r["reason"] == "LLM rejected: not actually personal data" for r in removed
        )

        # Primary's validation_summary back-references the sidecar by artifact_id.
        validation_summary = stored_primary.content["analysis_metadata"][
            "validation_summary"
        ]
        assert (
            validation_summary["removed_findings_artifact_id"]
            == "findings.removed_findings"
        )
