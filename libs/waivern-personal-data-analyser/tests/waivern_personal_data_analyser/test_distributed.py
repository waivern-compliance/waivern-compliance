"""Tests for PersonalDataAnalyser DistributedProcessor implementation.

Verifies the prepare/finalise/deserialise contract:
- prepare() runs pattern matching and builds an LLMRequest when enabled
- finalise() interprets dispatch results via the ValidationOrchestrator
- deserialise_prepare_result() round-trips through JSON serialisation

Uses synthetic rules via monkeypatched RulesetManager to decouple from
production ruleset data.
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
from waivern_rulesets.personal_data_indicator import PersonalDataIndicatorRule
from waivern_schemas.connector_types import BaseMetadata
from waivern_schemas.personal_data_indicator import PersonalDataIndicatorModel
from waivern_schemas.standard_input import (
    StandardInputDataItemModel,
    StandardInputDataModel,
)

from waivern_personal_data_analyser.analyser import PersonalDataAnalyser
from waivern_personal_data_analyser.prompts.prompt_builder import (
    PersonalDataPromptBuilder,
)
from waivern_personal_data_analyser.types import (
    PersonalDataAnalyserConfig,
    PersonalDataPrepareState,
)

OUTPUT_SCHEMA = Schema("personal_data_indicator", "1.0.0")
INPUT_SCHEMA = Schema("standard_input", "1.0.0")
RUN_ID = "test-run-id"

# =============================================================================
# Synthetic rules
# =============================================================================

RULE_EMAIL = PersonalDataIndicatorRule(
    name="Email Address",
    description="Email address detection",
    category="email",
    patterns=("email",),
)

RULE_PHONE = PersonalDataIndicatorRule(
    name="Phone Number",
    description="Phone number detection",
    category="phone",
    patterns=("phone",),
)

SYNTHETIC_RULES = (RULE_EMAIL, RULE_PHONE)

_UNUSED_RULESET_URI = "unused/test/1.0.0"


def _mock_get_rules(
    uri: str, rule_type: type[PersonalDataIndicatorRule]
) -> tuple[PersonalDataIndicatorRule, ...]:
    return SYNTHETIC_RULES


# =============================================================================
# Helpers
# =============================================================================


def _make_config(enable_llm: bool = True) -> PersonalDataAnalyserConfig:
    """Build a PersonalDataAnalyserConfig for tests."""
    return PersonalDataAnalyserConfig(
        pattern_matching=PatternMatchingConfig(ruleset=_UNUSED_RULESET_URI),
        llm_validation=LLMValidationConfig(
            enable_llm_validation=enable_llm,
            llm_validation_mode="standard",
        ),
    )


def _make_analyser(*, enable_llm: bool = True) -> PersonalDataAnalyser:
    """Build an analyser with controllable LLM enablement via config."""
    return PersonalDataAnalyser(config=_make_config(enable_llm))


def _make_message(content: str) -> Message:
    """Build a standard_input message carrying a single data item."""
    data = StandardInputDataModel(
        schemaVersion="1.0.0",
        name="test_data",
        data=[
            StandardInputDataItemModel(
                content=content,
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


def _make_no_pattern_message() -> Message:
    """Build a message whose content matches no personal-data patterns."""
    return _make_message("this content contains no personal data patterns")


def _make_email_phone_message() -> Message:
    """Build a message with two items carrying an email and a phone pattern."""
    data = StandardInputDataModel(
        schemaVersion="1.0.0",
        name="test_data",
        data=[
            StandardInputDataItemModel(
                content="Contact email: john.doe@company.com",
                metadata=BaseMetadata(source="email_source", connector_type="test"),
            ),
            StandardInputDataItemModel(
                content="Phone: +44 20 7123 4567",
                metadata=BaseMetadata(source="phone_source", connector_type="test"),
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
    request: LLMRequest[PersonalDataIndicatorModel],
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
        message = _make_email_phone_message()

        result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)

        assert len(result.requests) == 1
        assert result.state.llm_enabled is True
        assert result.state.orchestrator_state is not None
        assert len(result.state.all_findings) >= 2  # at least email + phone

        assert isinstance(result.requests[0], LLMRequest)
        llm_request = cast(LLMRequest[PersonalDataIndicatorModel], result.requests[0])
        assert llm_request.batching_mode == BatchingMode.COUNT_BASED
        assert isinstance(llm_request.prompt_builder, PersonalDataPromptBuilder)
        assert llm_request.response_model is LLMValidationResponseModel
        assert llm_request.run_id == RUN_ID

    def test_findings_with_llm_disabled_returns_empty_requests(self) -> None:
        """Findings with ``enable_llm_validation=False`` yield no dispatch requests."""
        analyser = _make_analyser(enable_llm=False)
        message = _make_email_phone_message()

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
        message = _make_email_phone_message()

        prepare_result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        finalise_outcome = analyser.finalise(prepare_result.state, [], OUTPUT_SCHEMA)
        assert isinstance(finalise_outcome, tuple)
        result, sidecars = finalise_outcome
        assert isinstance(result, Message)
        assert "validation_summary" not in result.content.get("analysis_metadata", {})
        # Findings preserved without filtering
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

    def test_validation_summary_pre_emits_removed_findings_artifact_id_as_none(
        self,
    ) -> None:
        """When validation ran, ``validation_summary.removed_findings_artifact_id`` is None.

        The analyser pre-emits ``None`` so the key is always present once
        validation ran; the executor overwrites it with the sidecar's
        artifact_id when removals occurred. Tests the analyser-side half of
        the audit-trail back-reference contract.
        """
        analyser = _make_analyser()
        message = _make_email_phone_message()

        prepare_result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        assert isinstance(prepare_result.requests[0], LLMRequest)
        llm_request = cast(
            LLMRequest[PersonalDataIndicatorModel], prepare_result.requests[0]
        )
        # No removals: every sampled finding TRUE_POSITIVE.
        sampled = prepare_result.state.orchestrator_state.strategy_findings  # pyright: ignore[reportOptionalMemberAccess]
        verdicts = {f.id: "TRUE_POSITIVE" for f in sampled}
        dispatch_result = _build_llm_dispatch_result(llm_request, verdicts)

        finalise_outcome = analyser.finalise(
            prepare_result.state, [dispatch_result], OUTPUT_SCHEMA
        )
        assert isinstance(finalise_outcome, tuple)
        result, _sidecars = finalise_outcome
        validation_summary = result.content["analysis_metadata"]["validation_summary"]
        assert validation_summary["removed_findings_artifact_id"] is None

    def test_llm_result_filters_false_positives_and_marks_kept(self) -> None:
        """LLM TRUE_POSITIVE/FALSE_POSITIVE verdicts → filtering + marking."""
        analyser = _make_analyser()
        message = _make_email_phone_message()

        prepare_result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        assert prepare_result.state.orchestrator_state is not None
        sampled = prepare_result.state.orchestrator_state.strategy_findings
        assert len(sampled) >= 2

        # Mark first as FALSE_POSITIVE, second as TRUE_POSITIVE
        assert isinstance(prepare_result.requests[0], LLMRequest)
        llm_request = cast(
            LLMRequest[PersonalDataIndicatorModel], prepare_result.requests[0]
        )
        verdicts = {
            sampled[0].id: "FALSE_POSITIVE",
            sampled[1].id: "TRUE_POSITIVE",
        }
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
        # TRUE_POSITIVE survives; FALSE_POSITIVE and its group may be removed
        kept_ids = {f["id"] for f in findings}
        assert sampled[1].id in kept_ids
        # TRUE_POSITIVE was LLM-validated → should be marked in metadata context
        kept_finding = next(f for f in findings if f["id"] == sampled[1].id)
        assert (
            kept_finding["metadata"]["context"].get("personal_data_llm_validated")
            is True
        )

        # FALSE_POSITIVE removal produced an audit-trail sidecar
        assert len(sidecars) == 1
        sidecar = sidecars[0]
        assert sidecar.schema == Schema("removed_findings", "1.0.0")
        assert sidecar.content["analyser_name"] == "personal_data_analyser"
        assert sidecar.content["run_id"] == RUN_ID
        assert sidecar.content["ruleset"] == _UNUSED_RULESET_URI
        assert len(sidecar.content["removed_findings"]) >= 1

    def test_sidecar_carries_serialised_finding_and_reason(self) -> None:
        """Each RemovedFinding has matching id and reason verbatim from the LLM verdict.

        Cascade-reason synthesis (``"Inferred — …"`` prefix) is exercised at
        the orchestrator layer (Step 3); here we only need to confirm that
        whatever ``reason`` the orchestrator attaches to a ``RemovedItem``
        reaches the sidecar entry verbatim.
        """
        analyser = _make_analyser()
        message = _make_email_phone_message()

        prepare_result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        assert prepare_result.state.orchestrator_state is not None
        sampled = prepare_result.state.orchestrator_state.strategy_findings

        # Mark all sampled findings FALSE_POSITIVE → every sample ends up in
        # removed_findings with the LLM verdict's reasoning attached.
        assert isinstance(prepare_result.requests[0], LLMRequest)
        llm_request = cast(
            LLMRequest[PersonalDataIndicatorModel], prepare_result.requests[0]
        )
        verdicts = {f.id: "FALSE_POSITIVE" for f in sampled}
        dispatch_result = _build_llm_dispatch_result(llm_request, verdicts)

        finalise_outcome = analyser.finalise(
            prepare_result.state, [dispatch_result], OUTPUT_SCHEMA
        )
        assert isinstance(finalise_outcome, tuple)
        _result, sidecars = finalise_outcome
        assert len(sidecars) == 1
        removed = sidecars[0].content["removed_findings"]
        assert len(removed) >= 1

        sampled_ids = {f.id for f in sampled}
        for entry in removed:
            assert entry["original_finding"]["id"] in sampled_ids
            # LLM-direct reasons preserve the verdict's reasoning verbatim.
            # _build_llm_dispatch_result attaches "test reasoning" to every result.
            assert entry["reason"] == "test reasoning"

    def test_missing_llm_result_treats_all_as_skipped_with_failure(self) -> None:
        """No LLM result (e.g. dispatcher error) → findings kept, all_succeeded=False."""
        analyser = _make_analyser()
        message = _make_email_phone_message()

        prepare_result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)

        # Empty results list: the orchestrator treats this as a failed dispatch
        # and all strategy findings are categorised as skipped (BATCH_ERROR).
        finalise_outcome = analyser.finalise(prepare_result.state, [], OUTPUT_SCHEMA)
        assert isinstance(finalise_outcome, tuple)
        result, sidecars = finalise_outcome
        assert isinstance(result, Message)
        metadata = result.content["analysis_metadata"]
        assert metadata["validation_summary"]["all_succeeded"] is False
        assert metadata["validation_summary"]["skipped_count"] > 0
        # Conservative keep: findings preserved
        assert len(result.content["findings"]) >= 1
        # BATCH_ERROR never reached the LLM → no removals → no audit content
        assert sidecars == []


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
        message = _make_email_phone_message()

        original = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        raw: dict[str, Any] = original.model_dump(mode="json")
        restored = analyser.deserialise_prepare_result(raw)

        # State fields
        assert isinstance(restored.state, PersonalDataPrepareState)
        assert restored.state.run_id == original.state.run_id
        assert restored.state.llm_enabled == original.state.llm_enabled
        assert len(restored.state.all_findings) == len(original.state.all_findings)
        assert isinstance(restored.state.orchestrator_state, OrchestratorPrepareState)
        assert restored.state.orchestrator_state.run_id == RUN_ID

        # Request metadata (prompt_builder/response_model are excluded)
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
        message = _make_email_phone_message()

        original = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        raw: dict[str, Any] = original.model_dump(mode="json")
        restored = analyser.deserialise_prepare_result(raw)

        assert restored.requests == []
        assert restored.state.orchestrator_state is None
        assert restored.state.llm_enabled is False
