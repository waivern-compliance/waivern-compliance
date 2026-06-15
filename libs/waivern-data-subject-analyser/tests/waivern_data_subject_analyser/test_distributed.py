"""Tests for DataSubjectAnalyser DistributedProcessor implementation.

Verifies the prepare/finalise/deserialise contract:
- prepare() runs pattern matching and builds an LLMRequest when enabled
- finalise() interprets dispatch results via the ValidationOrchestrator
- deserialise_prepare_result() round-trips through JSON serialisation

Uses monkeypatched RulesetManager to decouple from production ruleset data.
"""

from typing import Any, cast

import pytest
from waivern_analysers_shared.llm_validation.validation_orchestrator import (
    OrchestratorPrepareState,
)
from waivern_analysers_shared.types import LLMValidationConfig, PatternMatchingConfig
from waivern_analysers_shared.utilities import RulesetManager
from waivern_core import LLMValidationResponseModel, LLMValidationResultModel
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_llm.types import BatchingMode, LLMDispatchResult, LLMRequest
from waivern_rulesets.data_subject_indicator import DataSubjectIndicatorRule
from waivern_schemas.connector_types import BaseMetadata
from waivern_schemas.data_subject_indicator import DataSubjectIndicatorModel
from waivern_schemas.standard_input import (
    StandardInputDataItemModel,
    StandardInputDataModel,
)

from waivern_data_subject_analyser.analyser import DataSubjectAnalyser
from waivern_data_subject_analyser.prompts.prompt_builder import (
    DataSubjectPromptBuilder,
)
from waivern_data_subject_analyser.types import (
    DataSubjectAnalyserConfig,
    DataSubjectPrepareState,
)

# =============================================================================
# Synthetic rules
# =============================================================================

RULE_EMPLOYEE = DataSubjectIndicatorRule(
    name="Test Employee",
    description="Employee indicator",
    subject_category="test_employee",
    indicator_type="primary",
    confidence_weight=45,
    patterns=("test_employee_kw",),
)

RULE_CUSTOMER = DataSubjectIndicatorRule(
    name="Test Customer",
    description="Customer indicator",
    subject_category="test_customer",
    indicator_type="primary",
    confidence_weight=50,
    patterns=("test_customer_kw",),
)

SYNTHETIC_RULES = (RULE_EMPLOYEE, RULE_CUSTOMER)

_UNUSED_RULESET_URI = "unused/test/1.0.0"


def _mock_get_rules(
    uri: str, rule_type: type[DataSubjectIndicatorRule]
) -> tuple[DataSubjectIndicatorRule, ...]:
    return SYNTHETIC_RULES


# =============================================================================
# Helpers
# =============================================================================

OUTPUT_SCHEMA = Schema("data_subject_indicator", "1.0.0")
INPUT_SCHEMA = Schema("standard_input", "1.0.0")
RUN_ID = "test-run-id"


def _make_config(enable_llm: bool = True) -> DataSubjectAnalyserConfig:
    """Build a DataSubjectAnalyserConfig for tests."""
    return DataSubjectAnalyserConfig(
        pattern_matching=PatternMatchingConfig(ruleset=_UNUSED_RULESET_URI),
        llm_validation=LLMValidationConfig(
            enable_llm_validation=enable_llm,
            llm_validation_mode="standard",
        ),
    )


def _make_analyser(*, enable_llm: bool = True) -> DataSubjectAnalyser:
    """Build an analyser with controllable LLM enablement via config."""
    return DataSubjectAnalyser(config=_make_config(enable_llm))


def _make_no_pattern_message() -> Message:
    """Build a message whose content matches no data-subject patterns."""
    data = StandardInputDataModel(
        schemaVersion="1.0.0",
        name="test_data",
        data=[
            StandardInputDataItemModel(
                content="this content has no data subject patterns",
                metadata=BaseMetadata(source="test_source", connector_type="test"),
            )
        ],
    )
    return Message(
        id="test-message",
        content=data.model_dump(exclude_none=True),
        schema=INPUT_SCHEMA,
        run_id=RUN_ID,
    )


def _make_employee_customer_message() -> Message:
    """Build a message with items containing employee and customer indicators."""
    data = StandardInputDataModel(
        schemaVersion="1.0.0",
        name="test_data",
        data=[
            StandardInputDataItemModel(
                content="test_customer_kw field in database table",
                metadata=BaseMetadata(source="customer_source", connector_type="test"),
            ),
            StandardInputDataItemModel(
                content="test_employee_kw records with identifiers",
                metadata=BaseMetadata(source="employee_source", connector_type="test"),
            ),
        ],
    )
    return Message(
        id="test-message",
        content=data.model_dump(exclude_none=True),
        schema=INPUT_SCHEMA,
        run_id=RUN_ID,
    )


def _build_llm_dispatch_result(
    request: LLMRequest[DataSubjectIndicatorModel],
    verdicts: dict[str, str],
) -> LLMDispatchResult:
    """Build an LLMDispatchResult mapping finding IDs to validation verdicts.

    Args:
        request: The originating LLMRequest (for request_id matching).
        verdicts: Mapping of finding_id to "TRUE_POSITIVE" or "FALSE_POSITIVE".

    """
    results = [
        LLMValidationResultModel(
            finding_id=finding_id,
            validation_result="TRUE_POSITIVE"
            if verdict == "TRUE_POSITIVE"
            else "FALSE_POSITIVE",
            confidence=0.9,
            reasoning="test reasoning",
            recommended_action="keep" if verdict == "TRUE_POSITIVE" else "discard",
        )
        for finding_id, verdict in verdicts.items()
    ]
    response = LLMValidationResponseModel(results=results)
    return LLMDispatchResult(
        request_id=request.request_id,
        model_name="claude-sonnet-4-5-20250929",
        responses=[response.model_dump(mode="json")],
        skipped=[],
    )


# =============================================================================
# Prepare
# =============================================================================


class TestPrepare:
    """Tests for prepare() — pattern matching and request building."""

    @pytest.fixture(autouse=True)
    def _mock_ruleset_manager(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Inject synthetic rules so the analyser doesn't need real rulesets."""
        monkeypatch.setattr(RulesetManager, "get_rules", _mock_get_rules)

    def test_no_findings_returns_empty_requests(self) -> None:
        """No pattern matches → empty requests and orchestrator_state=None."""
        analyser = _make_analyser()
        message = _make_no_pattern_message()

        result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)

        assert result.requests == []
        assert result.state.all_findings == []
        assert result.state.orchestrator_state is None
        assert result.state.llm_enabled is True

    def test_findings_with_llm_enabled_builds_llm_request(self) -> None:
        """Findings + LLM enabled → LLMRequest with expected shape."""
        analyser = _make_analyser()
        message = _make_employee_customer_message()

        result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)

        assert len(result.requests) == 1
        assert result.state.llm_enabled is True
        assert result.state.orchestrator_state is not None
        assert len(result.state.all_findings) >= 2

        assert isinstance(result.requests[0], LLMRequest)
        llm_request = cast(LLMRequest[DataSubjectIndicatorModel], result.requests[0])
        assert llm_request.batching_mode == BatchingMode.COUNT_BASED
        assert isinstance(llm_request.prompt_builder, DataSubjectPromptBuilder)
        assert llm_request.response_model is LLMValidationResponseModel
        assert llm_request.run_id == RUN_ID

    def test_findings_with_llm_disabled_returns_empty_requests(self) -> None:
        """Findings with ``enable_llm_validation=False`` yield no dispatch requests."""
        analyser = _make_analyser(enable_llm=False)
        message = _make_employee_customer_message()

        result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)

        assert result.requests == []
        assert result.state.llm_enabled is False
        assert result.state.orchestrator_state is None
        assert len(result.state.all_findings) >= 2


# =============================================================================
# Finalise
# =============================================================================


class TestFinalise:
    """Tests for finalise() — result interpretation and output building."""

    @pytest.fixture(autouse=True)
    def _mock_ruleset_manager(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Inject synthetic rules so the analyser doesn't need real rulesets."""
        monkeypatch.setattr(RulesetManager, "get_rules", _mock_get_rules)

    def test_llm_disabled_produces_output_without_validation_summary(self) -> None:
        """llm_enabled=False state → output message with no validation_summary."""
        analyser = _make_analyser(enable_llm=False)
        message = _make_employee_customer_message()

        prepare_result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        finalise_outcome = analyser.finalise(prepare_result.state, [], OUTPUT_SCHEMA)
        assert isinstance(finalise_outcome, tuple)
        result, sidecars = finalise_outcome
        assert isinstance(result, Message)
        assert "validation_summary" not in result.content.get("analysis_metadata", {})
        assert len(result.content["findings"]) == len(prepare_result.state.all_findings)
        # LLM never ran → no audit content
        assert sidecars == []

    def test_no_findings_produces_empty_output(self) -> None:
        """Empty findings state → empty output, no validation_summary."""
        analyser = _make_analyser()
        message = _make_no_pattern_message()

        prepare_result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        finalise_outcome = analyser.finalise(prepare_result.state, [], OUTPUT_SCHEMA)
        assert isinstance(finalise_outcome, tuple)
        result, sidecars = finalise_outcome
        assert isinstance(result, Message)
        assert result.content["findings"] == []
        assert "validation_summary" not in result.content.get("analysis_metadata", {})
        # No findings → no removals → no audit content
        assert sidecars == []

    def test_llm_result_filters_false_positives_and_marks_kept(self) -> None:
        """LLM TRUE_POSITIVE/FALSE_POSITIVE verdicts → filtering + marking."""
        analyser = _make_analyser()
        message = _make_employee_customer_message()

        prepare_result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        assert prepare_result.state.orchestrator_state is not None
        sampled = prepare_result.state.orchestrator_state.strategy_findings
        assert len(sampled) >= 2

        assert isinstance(prepare_result.requests[0], LLMRequest)
        llm_request = cast(
            LLMRequest[DataSubjectIndicatorModel], prepare_result.requests[0]
        )
        verdicts = {f.id: "TRUE_POSITIVE" for f in sampled}
        dispatch_result = _build_llm_dispatch_result(llm_request, verdicts)

        finalise_outcome = analyser.finalise(
            prepare_result.state, [dispatch_result], OUTPUT_SCHEMA
        )
        assert isinstance(finalise_outcome, tuple)
        result, sidecars = finalise_outcome
        assert isinstance(result, Message)
        metadata = result.content["analysis_metadata"]
        assert "validation_summary" in metadata
        assert metadata["validation_summary"]["all_succeeded"] is True

        findings = result.content["findings"]
        sampled_ids = {f.id for f in sampled}
        for finding in findings:
            if finding["id"] in sampled_ids:
                assert (
                    finding["metadata"]["context"].get("data_subject_llm_validated")
                    is True
                )
        # All-TRUE_POSITIVE verdicts → no removals → no audit content
        assert sidecars == []

    def test_missing_llm_result_treats_all_as_skipped_with_failure(self) -> None:
        """No LLM result (e.g. dispatcher error) → findings kept, all_succeeded=False.

        Conservative-keep contract: when dispatch fails, every original
        finding must still be present in the output and the failure surfaces
        in validation_summary rather than being silently hidden.
        """
        analyser = _make_analyser()
        message = _make_employee_customer_message()

        prepare_result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        original_count = len(prepare_result.state.all_findings)

        finalise_outcome = analyser.finalise(prepare_result.state, [], OUTPUT_SCHEMA)
        assert isinstance(finalise_outcome, tuple)
        result, sidecars = finalise_outcome
        assert isinstance(result, Message)
        metadata = result.content["analysis_metadata"]
        assert metadata["validation_summary"]["all_succeeded"] is False
        assert metadata["validation_summary"]["skipped_count"] > 0
        assert len(result.content["findings"]) == original_count
        # BATCH_ERROR never reached the LLM → no removals → no audit content
        assert sidecars == []

    def test_sidecar_carries_serialised_finding_and_reason(self) -> None:
        """FALSE_POSITIVE removals → one sidecar with identity fields and serialised entries.

        Cascade-reason synthesis (``"Inferred — …"`` prefix) is exercised at
        the orchestrator layer (Step 3); here we only need to confirm that
        whatever ``reason`` the orchestrator attaches to a ``RemovedItem``
        reaches the sidecar entry verbatim, and that the wrapper carries the
        analyser identity for cross-artifact correlation.
        """
        analyser = _make_analyser()
        message = _make_employee_customer_message()

        prepare_result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        assert prepare_result.state.orchestrator_state is not None
        sampled = prepare_result.state.orchestrator_state.strategy_findings

        assert isinstance(prepare_result.requests[0], LLMRequest)
        llm_request = cast(
            LLMRequest[DataSubjectIndicatorModel], prepare_result.requests[0]
        )
        verdicts = {f.id: "FALSE_POSITIVE" for f in sampled}
        dispatch_result = _build_llm_dispatch_result(llm_request, verdicts)

        finalise_outcome = analyser.finalise(
            prepare_result.state, [dispatch_result], OUTPUT_SCHEMA
        )
        assert isinstance(finalise_outcome, tuple)
        _result, sidecars = finalise_outcome
        assert len(sidecars) == 1
        sidecar = sidecars[0]
        assert sidecar.schema == Schema("removed_findings", "1.0.0")
        assert sidecar.content["analyser_name"] == "data_subject_analyser"
        assert sidecar.content["run_id"] == RUN_ID
        assert sidecar.content["ruleset"] == _UNUSED_RULESET_URI

        removed = sidecar.content["removed_findings"]
        assert len(removed) >= 1
        sampled_ids = {f.id for f in sampled}
        for entry in removed:
            assert entry["original_finding"]["id"] in sampled_ids
            # LLM-direct reasons preserve the verdict's reasoning verbatim.
            # _build_llm_dispatch_result attaches "test reasoning" to every result.
            assert entry["reason"] == "test reasoning"


# =============================================================================
# Deserialise
# =============================================================================


class TestDeserialise:
    """Tests for deserialise_prepare_result() round-trip fidelity."""

    @pytest.fixture(autouse=True)
    def _mock_ruleset_manager(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Inject synthetic rules so the analyser doesn't need real rulesets."""
        monkeypatch.setattr(RulesetManager, "get_rules", _mock_get_rules)

    def test_round_trip_with_llm_request(self) -> None:
        """prepare() → model_dump → deserialise → equivalent state and request.

        Validates the resume path: the executor persists PrepareResult via
        ``model_dump(mode="json")`` and restores it via
        ``deserialise_prepare_result()``. State fields and request metadata
        must survive the round-trip.
        """
        analyser = _make_analyser()
        message = _make_employee_customer_message()

        original = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        raw: dict[str, Any] = original.model_dump(mode="json")
        restored = analyser.deserialise_prepare_result(raw)

        assert isinstance(restored.state, DataSubjectPrepareState)
        assert restored.state.run_id == original.state.run_id
        assert restored.state.llm_enabled == original.state.llm_enabled
        assert len(restored.state.all_findings) == len(original.state.all_findings)
        assert isinstance(restored.state.orchestrator_state, OrchestratorPrepareState)
        assert restored.state.orchestrator_state.run_id == RUN_ID

        assert len(restored.requests) == len(original.requests)
        assert restored.requests[0].request_id == original.requests[0].request_id
        original_llm_request = original.requests[0]
        restored_llm_request = restored.requests[0]
        assert isinstance(original_llm_request, LLMRequest)
        assert isinstance(restored_llm_request, LLMRequest)
        assert restored_llm_request.batching_mode == original_llm_request.batching_mode
        assert restored_llm_request.run_id == original_llm_request.run_id

    def test_round_trip_without_llm_request(self) -> None:
        """Round-trip when LLM disabled: orchestrator_state=None, no requests."""
        analyser = _make_analyser(enable_llm=False)
        message = _make_employee_customer_message()

        original = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        raw: dict[str, Any] = original.model_dump(mode="json")
        restored = analyser.deserialise_prepare_result(raw)

        assert restored.requests == []
        assert restored.state.orchestrator_state is None
        assert restored.state.llm_enabled is False
