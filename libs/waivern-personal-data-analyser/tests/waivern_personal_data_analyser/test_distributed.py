"""Tests for PersonalDataAnalyser DistributedProcessor implementation.

Verifies the prepare/finalise/deserialise contract:
- prepare() runs pattern matching and builds an LLMRequest when enabled
- finalise() interprets dispatch results via the ValidationOrchestrator
- deserialise_prepare_result() round-trips through JSON serialisation
"""

from typing import Any, cast
from unittest.mock import Mock

from waivern_analysers_shared.llm_validation.models import (
    LLMValidationResponseModel,
    LLMValidationResultModel,
)
from waivern_analysers_shared.llm_validation.validation_orchestrator import (
    OrchestratorPrepareState,
)
from waivern_analysers_shared.types import LLMValidationConfig, PatternMatchingConfig
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_llm import LLMService
from waivern_llm.types import BatchingMode, LLMDispatchResult, LLMRequest
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
# Helpers
# =============================================================================


def _make_config(enable_llm: bool = True) -> PersonalDataAnalyserConfig:
    """Build a PersonalDataAnalyserConfig for tests."""
    return PersonalDataAnalyserConfig(
        pattern_matching=PatternMatchingConfig(
            ruleset="local/personal_data_indicator/1.0.0"
        ),
        llm_validation=LLMValidationConfig(
            enable_llm_validation=enable_llm,
            llm_validation_mode="standard",
        ),
    )


def _make_analyser(
    *,
    enable_llm: bool = True,
    with_service: bool = True,
) -> PersonalDataAnalyser:
    """Build an analyser with controllable LLM enablement.

    Args:
        enable_llm: Sets ``config.llm_validation.enable_llm_validation``.
        with_service: When True, injects a mock ``LLMService``; when False,
            injects ``None`` (representing a missing capability).

    """
    service: LLMService | None = Mock(spec=LLMService) if with_service else None
    return PersonalDataAnalyser(config=_make_config(enable_llm), llm_service=service)


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

    def test_findings_without_llm_service_returns_empty_requests(self) -> None:
        """Findings + no LLM service → empty requests, llm_enabled=False."""
        analyser = _make_analyser(with_service=False)
        message = _make_email_phone_message()

        result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)

        assert result.requests == []
        assert result.state.llm_enabled is False
        assert result.state.orchestrator_state is None
        assert len(result.state.all_findings) >= 2

    def test_findings_with_llm_disabled_in_config_returns_empty_requests(self) -> None:
        """Findings + LLM service but config disables → empty requests.

        Both signals must agree: a present service alone is not enough when
        the caller has opted out via ``enable_llm_validation=False``.
        """
        analyser = _make_analyser(enable_llm=False, with_service=True)
        message = _make_email_phone_message()

        result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)

        assert result.requests == []
        assert result.state.llm_enabled is False
        assert result.state.orchestrator_state is None


# =============================================================================
# Finalise
# =============================================================================


class TestFinalise:
    """Tests for finalise() — result interpretation and output building."""

    def test_llm_disabled_produces_output_without_validation_summary(self) -> None:
        """llm_enabled=False state → output message with no validation_summary."""
        analyser = _make_analyser(with_service=False)
        message = _make_email_phone_message()

        prepare_result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        result = analyser.finalise(prepare_result.state, [], OUTPUT_SCHEMA)

        assert isinstance(result, Message)
        assert "validation_summary" not in result.content.get("analysis_metadata", {})
        # Findings preserved without filtering
        assert len(result.content["findings"]) == len(prepare_result.state.all_findings)

    def test_no_findings_produces_empty_output(self) -> None:
        """Empty findings state → empty output, no validation_summary."""
        analyser = _make_analyser()
        message = _make_no_pattern_message()

        prepare_result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        result = analyser.finalise(prepare_result.state, [], OUTPUT_SCHEMA)

        assert isinstance(result, Message)
        assert result.content["findings"] == []
        assert "validation_summary" not in result.content.get("analysis_metadata", {})

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

        result = analyser.finalise(
            prepare_result.state, [dispatch_result], OUTPUT_SCHEMA
        )

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

    def test_missing_llm_result_treats_all_as_skipped_with_failure(self) -> None:
        """No LLM result (e.g. dispatcher error) → findings kept, all_succeeded=False."""
        analyser = _make_analyser()
        message = _make_email_phone_message()

        prepare_result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)

        # Empty results list: the orchestrator treats this as a failed dispatch
        # and all strategy findings are categorised as skipped (BATCH_ERROR).
        result = analyser.finalise(prepare_result.state, [], OUTPUT_SCHEMA)

        assert isinstance(result, Message)
        metadata = result.content["analysis_metadata"]
        assert metadata["validation_summary"]["all_succeeded"] is False
        assert metadata["validation_summary"]["skipped_count"] > 0
        # Conservative keep: findings preserved
        assert len(result.content["findings"]) >= 1


# =============================================================================
# Process (degraded fallback)
# =============================================================================


class TestProcessDegradedFallback:
    """Tests for process() — standalone degraded-mode wrapper."""

    def test_process_never_calls_llm_even_when_configured(self) -> None:
        """process() delegates to prepare/finalise with LLM forced off."""
        service = Mock(spec=LLMService)
        analyser = PersonalDataAnalyser(config=_make_config(), llm_service=service)
        message = _make_email_phone_message()

        result = analyser.process([message], OUTPUT_SCHEMA)

        assert isinstance(result, Message)
        # No validation_summary because process() degrades LLM to off
        assert "validation_summary" not in result.content.get("analysis_metadata", {})
        # Mock service was never invoked
        assert not service.method_calls


# =============================================================================
# Deserialise
# =============================================================================


class TestDeserialise:
    """Tests for deserialise_prepare_result() round-trip fidelity."""

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
        analyser = _make_analyser(with_service=False)
        message = _make_email_phone_message()

        original = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        raw: dict[str, Any] = original.model_dump(mode="json")
        restored = analyser.deserialise_prepare_result(raw)

        assert restored.requests == []
        assert restored.state.orchestrator_state is None
        assert restored.state.llm_enabled is False
