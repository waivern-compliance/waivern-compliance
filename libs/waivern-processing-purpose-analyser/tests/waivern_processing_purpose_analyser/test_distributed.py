"""Tests for ProcessingPurposeAnalyser DistributedProcessor implementation.

Verifies the prepare/finalise/deserialise contract, including multi-round
dispatch when the source_code primary strategy produces fallback-eligible
skipped findings.
"""

from typing import Any, cast

from waivern_analysers_shared.llm_validation.validation_orchestrator import (
    OrchestratorPrepareState,
)
from waivern_analysers_shared.types import LLMValidationConfig, PatternMatchingConfig
from waivern_core import LLMValidationResponseModel, LLMValidationResultModel
from waivern_core.dispatch import PrepareResult
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_llm import SkippedFinding, SkipReason
from waivern_llm.types import BatchingMode, LLMDispatchResult, LLMRequest
from waivern_schemas.connector_types import BaseMetadata
from waivern_schemas.processing_purpose_indicator import ProcessingPurposeIndicatorModel
from waivern_schemas.source_code import (
    SourceCodeAnalysisMetadataModel,
    SourceCodeDataModel,
    SourceCodeFileDataModel,
    SourceCodeFileMetadataModel,
)
from waivern_schemas.standard_input import (
    StandardInputDataItemModel,
    StandardInputDataModel,
)

from waivern_processing_purpose_analyser.analyser import ProcessingPurposeAnalyser
from waivern_processing_purpose_analyser.prompts import (
    ProcessingPurposePromptBuilder,
    SourceCodePromptBuilder,
)
from waivern_processing_purpose_analyser.types import (
    ProcessingPurposeAnalyserConfig,
    ProcessingPurposePrepareState,
)

OUTPUT_SCHEMA = Schema("processing_purpose_indicator", "1.0.0")
STANDARD_SCHEMA = Schema("standard_input", "1.0.0")
SOURCE_SCHEMA = Schema("source_code", "1.0.0")
RUN_ID = "test-run-id"


# =============================================================================
# Helpers
# =============================================================================


def _make_config(enable_llm: bool = True) -> ProcessingPurposeAnalyserConfig:
    """Build a ProcessingPurposeAnalyserConfig for tests."""
    return ProcessingPurposeAnalyserConfig(
        pattern_matching=PatternMatchingConfig(
            ruleset="local/processing_purposes/1.0.0"
        ),
        llm_validation=LLMValidationConfig(
            enable_llm_validation=enable_llm,
            llm_validation_mode="standard",
        ),
    )


def _make_analyser(*, enable_llm: bool = True) -> ProcessingPurposeAnalyser:
    """Build an analyser with controllable LLM enablement via config."""
    return ProcessingPurposeAnalyser(config=_make_config(enable_llm))


def _make_no_pattern_message() -> Message:
    """Build a standard_input message with content that matches no patterns."""
    data = StandardInputDataModel(
        schemaVersion="1.0.0",
        name="test_data",
        data=[
            StandardInputDataItemModel(
                content="this content has no processing purpose patterns",
                metadata=BaseMetadata(source="test_source", connector_type="test"),
            )
        ],
    )
    return Message(
        id="test-message",
        content=data.model_dump(exclude_none=True),
        schema=STANDARD_SCHEMA,
        run_id=RUN_ID,
    )


def _make_standard_input_purpose_message() -> Message:
    """Build a standard_input message containing processing-purpose indicators."""
    data = StandardInputDataModel(
        schemaVersion="1.0.0",
        name="test_data",
        data=[
            StandardInputDataItemModel(
                content="process customer payment transactions",
                metadata=BaseMetadata(source="payments_db", connector_type="test"),
            ),
            StandardInputDataItemModel(
                content="send marketing email campaigns to subscribers",
                metadata=BaseMetadata(source="marketing_svc", connector_type="test"),
            ),
        ],
    )
    return Message(
        id="test-message",
        content=data.model_dump(exclude_none=True),
        schema=STANDARD_SCHEMA,
        run_id=RUN_ID,
    )


def _make_source_code_message(files: dict[str, str]) -> Message:
    """Build a source_code Message from a {path: content} map."""
    file_data = [
        SourceCodeFileDataModel(
            file_path=path,
            language="php",
            raw_content=content,
            metadata=SourceCodeFileMetadataModel(
                file_size=len(content),
                line_count=content.count("\n") + 1,
                last_modified="2024-01-01T00:00:00Z",
            ),
        )
        for path, content in files.items()
    ]
    source_data = SourceCodeDataModel(
        schemaVersion="1.0.0",
        name="Source repo",
        description="Test source code",
        source="source",
        metadata=SourceCodeAnalysisMetadataModel(
            total_files=len(files),
            total_lines=sum(c.count("\n") + 1 for c in files.values()),
            analysis_timestamp="2024-01-01T00:00:00Z",
        ),
        data=file_data,
    )
    return Message(
        id="test-source",
        content=source_data.model_dump(exclude_none=True),
        schema=SOURCE_SCHEMA,
        run_id=RUN_ID,
    )


def _make_source_code_message_with_purposes() -> Message:
    """Build a source_code Message containing processing-purpose patterns."""
    return _make_source_code_message(
        {
            "src/PaymentService.php": (
                "<?php\n"
                "class PaymentService {\n"
                "    public function processPayment() {\n"
                "        // process customer payment transactions\n"
                "    }\n"
                "}\n"
            ),
            "src/MarketingService.php": (
                "<?php\n"
                "class MarketingService {\n"
                "    public function sendEmail() {\n"
                "        // send marketing email campaigns to subscribers\n"
                "    }\n"
                "}\n"
            ),
        }
    )


def _build_llm_dispatch_result(
    request: LLMRequest[ProcessingPurposeIndicatorModel],
    verdicts: dict[str, str],
    skipped: list[SkippedFinding[ProcessingPurposeIndicatorModel]] | None = None,
) -> LLMDispatchResult:
    """Build an LLMDispatchResult mapping finding IDs to verdicts (+ skipped list)."""
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
        skipped=list(skipped) if skipped else [],
    )


# =============================================================================
# Prepare
# =============================================================================


class TestPrepare:
    """Tests for prepare() — pattern matching, request building, strategy_state capture."""

    def test_no_findings_returns_empty_requests(self) -> None:
        """No pattern matches → empty requests and orchestrator_state=None."""
        analyser = _make_analyser()
        message = _make_no_pattern_message()

        result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)

        assert result.requests == []
        assert result.state.all_findings == []
        assert result.state.orchestrator_state is None
        assert result.state.llm_enabled is True
        assert result.state.input_schema_name == "standard_input"

    def test_standard_input_findings_with_llm_enabled_builds_llm_request(self) -> None:
        """Findings + LLM enabled (standard_input) → COUNT_BASED LLMRequest."""
        analyser = _make_analyser()
        message = _make_standard_input_purpose_message()

        result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)

        assert len(result.requests) == 1
        assert result.state.llm_enabled is True
        assert result.state.orchestrator_state is not None
        assert len(result.state.all_findings) >= 1

        assert isinstance(result.requests[0], LLMRequest)
        llm_request = cast(
            LLMRequest[ProcessingPurposeIndicatorModel], result.requests[0]
        )
        assert llm_request.batching_mode == BatchingMode.COUNT_BASED
        assert isinstance(llm_request.prompt_builder, ProcessingPurposePromptBuilder)
        assert llm_request.run_id == RUN_ID

    def test_findings_with_llm_disabled_returns_empty_requests(self) -> None:
        """Findings with ``enable_llm_validation=False`` yield no dispatch requests."""
        analyser = _make_analyser(enable_llm=False)
        message = _make_standard_input_purpose_message()

        result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)

        assert result.requests == []
        assert result.state.llm_enabled is False
        assert result.state.orchestrator_state is None

    def test_source_code_input_captures_strategy_state_with_source_contents(
        self,
    ) -> None:
        """source_code input → orchestrator_state.strategy_state carries source_contents."""
        analyser = _make_analyser()
        message = _make_source_code_message_with_purposes()

        result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)

        assert result.state.input_schema_name == "source_code"
        assert result.state.orchestrator_state is not None
        strategy_state = result.state.orchestrator_state.strategy_state
        assert strategy_state is not None
        assert "source_contents" in strategy_state
        source_contents = strategy_state["source_contents"]
        assert isinstance(source_contents, dict)
        assert "src/PaymentService.php" in source_contents
        assert "src/MarketingService.php" in source_contents

        # Source_code path uses EXTENDED_CONTEXT batching
        assert isinstance(result.requests[0], LLMRequest)
        llm_request = cast(
            LLMRequest[ProcessingPurposeIndicatorModel], result.requests[0]
        )
        assert llm_request.batching_mode == BatchingMode.EXTENDED_CONTEXT
        assert isinstance(llm_request.prompt_builder, SourceCodePromptBuilder)

    def test_standard_input_leaves_strategy_state_none(self) -> None:
        """standard_input input → orchestrator_state.strategy_state is None."""
        analyser = _make_analyser()
        message = _make_standard_input_purpose_message()

        result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)

        assert result.state.orchestrator_state is not None
        assert result.state.orchestrator_state.strategy_state is None


# =============================================================================
# Finalise (single round)
# =============================================================================


class TestFinalise:
    """Tests for finalise() single-round paths."""

    def test_llm_disabled_produces_output_without_validation_summary(self) -> None:
        """llm_enabled=False state → output message with no validation_summary."""
        analyser = _make_analyser(enable_llm=False)
        message = _make_standard_input_purpose_message()

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

    def test_llm_result_filters_false_positives_and_marks_kept(self) -> None:
        """LLM TRUE_POSITIVE/FALSE_POSITIVE verdicts → filtering + marker."""
        analyser = _make_analyser()
        message = _make_standard_input_purpose_message()

        prepare_result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        assert prepare_result.state.orchestrator_state is not None
        sampled = prepare_result.state.orchestrator_state.strategy_findings
        assert len(sampled) >= 1

        assert isinstance(prepare_result.requests[0], LLMRequest)
        llm_request = cast(
            LLMRequest[ProcessingPurposeIndicatorModel], prepare_result.requests[0]
        )
        # Mark every sampled finding TRUE_POSITIVE so all groups have a decision
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
                    finding["metadata"]["context"].get(
                        "processing_purpose_llm_validated"
                    )
                    is True
                )
        # All-TRUE_POSITIVE verdicts → no removals → no audit content
        assert sidecars == []

    def test_missing_llm_result_treats_all_as_skipped_with_failure(self) -> None:
        """No LLM result (e.g. dispatcher error) → findings kept, all_succeeded=False.

        Conservative-keep contract: when dispatch fails, every original finding
        must still be present in the output and the failure surfaces in
        validation_summary rather than being silently hidden.
        """
        analyser = _make_analyser()
        message = _make_standard_input_purpose_message()

        prepare_result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        original_count = len(prepare_result.state.all_findings)

        # Empty results list: orchestrator treats this as a failed dispatch
        # and every strategy finding is categorised as skipped (BATCH_ERROR).
        finalise_outcome = analyser.finalise(prepare_result.state, [], OUTPUT_SCHEMA)
        assert isinstance(finalise_outcome, tuple)
        result, sidecars = finalise_outcome
        assert isinstance(result, Message)
        metadata = result.content["analysis_metadata"]
        assert metadata["validation_summary"]["all_succeeded"] is False
        assert metadata["validation_summary"]["skipped_count"] > 0
        # Conservative keep: every original finding preserved
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
        message = _make_standard_input_purpose_message()

        prepare_result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        assert prepare_result.state.orchestrator_state is not None
        sampled = prepare_result.state.orchestrator_state.strategy_findings

        assert isinstance(prepare_result.requests[0], LLMRequest)
        llm_request = cast(
            LLMRequest[ProcessingPurposeIndicatorModel], prepare_result.requests[0]
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
        assert sidecar.content["analyser_name"] == "processing_purpose_analyser"
        assert sidecar.content["run_id"] == RUN_ID
        assert sidecar.content["ruleset"] == "local/processing_purposes/1.0.0"

        removed = sidecar.content["removed_findings"]
        assert len(removed) >= 1
        sampled_ids = {f.id for f in sampled}
        for entry in removed:
            assert entry["original_finding"]["id"] in sampled_ids
            # LLM-direct reasons preserve the verdict's reasoning verbatim.
            # _build_llm_dispatch_result attaches "test reasoning" to every result.
            assert entry["reason"] == "test reasoning"


# =============================================================================
# Finalise (multi-round) — Step 13 headline coverage
# =============================================================================


class TestFinaliseMultiRound:
    """Tests for the multi-round fallback mechanism in finalise()."""

    def test_source_code_with_oversized_skipped_triggers_fallback_prepare_result(
        self,
    ) -> None:
        """Round 1 primary with OVERSIZED skipped → finalise returns PrepareResult for fallback."""
        analyser = _make_analyser()
        message = _make_source_code_message_with_purposes()

        prepare_result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        assert prepare_result.state.orchestrator_state is not None
        sampled = prepare_result.state.orchestrator_state.strategy_findings
        assert len(sampled) >= 2

        # Round 1: mark first finding OVERSIZED (fallback-eligible),
        # second TRUE_POSITIVE.
        assert isinstance(prepare_result.requests[0], LLMRequest)
        llm_request = cast(
            LLMRequest[ProcessingPurposeIndicatorModel], prepare_result.requests[0]
        )
        verdicts = {sampled[1].id: "TRUE_POSITIVE"}
        skipped = [SkippedFinding(finding=sampled[0], reason=SkipReason.OVERSIZED)]
        primary_result = _build_llm_dispatch_result(
            llm_request, verdicts, skipped=skipped
        )

        outcome = analyser.finalise(
            prepare_result.state, [primary_result], OUTPUT_SCHEMA
        )

        # Fallback signal: PrepareResult, not Message
        assert isinstance(outcome, PrepareResult)
        assert len(outcome.requests) == 1
        assert outcome.state.orchestrator_state is not None
        assert outcome.state.orchestrator_state.is_fallback_round is True
        assert outcome.state.orchestrator_state.primary_outcome is not None
        # Only the OVERSIZED finding is sent for fallback
        fallback_findings = outcome.state.orchestrator_state.strategy_findings
        assert [f.id for f in fallback_findings] == [sampled[0].id]
        # input_schema_name and all_findings preserved
        assert outcome.state.input_schema_name == "source_code"
        assert outcome.state.all_findings == prepare_result.state.all_findings

    def test_fallback_round_merges_results_and_returns_message(self) -> None:
        """Round 2 (is_fallback_round=True) → merged Message, not another round."""
        analyser = _make_analyser()
        message = _make_source_code_message_with_purposes()

        prepare_result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        assert prepare_result.state.orchestrator_state is not None
        sampled = prepare_result.state.orchestrator_state.strategy_findings
        assert len(sampled) >= 2

        # Round 1 → returns PrepareResult (OVERSIZED triggers fallback)
        assert isinstance(prepare_result.requests[0], LLMRequest)
        primary_request = cast(
            LLMRequest[ProcessingPurposeIndicatorModel], prepare_result.requests[0]
        )
        primary_result = _build_llm_dispatch_result(
            primary_request,
            verdicts={sampled[1].id: "TRUE_POSITIVE"},
            skipped=[SkippedFinding(finding=sampled[0], reason=SkipReason.OVERSIZED)],
        )
        round_two_prep = analyser.finalise(
            prepare_result.state, [primary_result], OUTPUT_SCHEMA
        )
        assert isinstance(round_two_prep, PrepareResult)

        # Round 2 → fallback validates sampled[0] as TRUE_POSITIVE
        assert isinstance(round_two_prep.requests[0], LLMRequest)
        fallback_request = cast(
            LLMRequest[ProcessingPurposeIndicatorModel], round_two_prep.requests[0]
        )
        fallback_result = _build_llm_dispatch_result(
            fallback_request,
            verdicts={sampled[0].id: "TRUE_POSITIVE"},
        )

        finalise_outcome = analyser.finalise(
            round_two_prep.state, [fallback_result], OUTPUT_SCHEMA
        )
        assert isinstance(finalise_outcome, tuple)
        final, sidecars = finalise_outcome
        assert isinstance(final, Message)
        metadata = final.content["analysis_metadata"]
        assert "validation_summary" in metadata
        # Both rounds verdicted TRUE_POSITIVE → no removals → no audit content
        assert sidecars == []

    def test_source_code_without_eligible_skipped_completes_in_single_round(
        self,
    ) -> None:
        """No fallback-eligible skipped → finalise returns Message directly."""
        analyser = _make_analyser()
        message = _make_source_code_message_with_purposes()

        prepare_result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        assert prepare_result.state.orchestrator_state is not None
        sampled = prepare_result.state.orchestrator_state.strategy_findings

        assert isinstance(prepare_result.requests[0], LLMRequest)
        llm_request = cast(
            LLMRequest[ProcessingPurposeIndicatorModel], prepare_result.requests[0]
        )
        # All TRUE_POSITIVE, no skipped entries
        dispatch_result = _build_llm_dispatch_result(
            llm_request, verdicts={f.id: "TRUE_POSITIVE" for f in sampled}
        )

        finalise_outcome = analyser.finalise(
            prepare_result.state, [dispatch_result], OUTPUT_SCHEMA
        )
        assert isinstance(finalise_outcome, tuple)
        outcome, sidecars = finalise_outcome
        assert isinstance(outcome, Message)
        # All TRUE_POSITIVE → no removals → no audit content
        assert sidecars == []

    def test_fallback_round_marker_applied_to_both_primary_and_fallback_kept(
        self,
    ) -> None:
        """Marker applied to kept findings from both rounds."""
        analyser = _make_analyser()
        message = _make_source_code_message_with_purposes()

        prepare_result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        assert prepare_result.state.orchestrator_state is not None
        sampled = prepare_result.state.orchestrator_state.strategy_findings
        assert len(sampled) >= 2

        primary_kept = sampled[1]
        fallback_kept = sampled[0]

        # Round 1
        assert isinstance(prepare_result.requests[0], LLMRequest)
        primary_request = cast(
            LLMRequest[ProcessingPurposeIndicatorModel], prepare_result.requests[0]
        )
        primary_result = _build_llm_dispatch_result(
            primary_request,
            verdicts={primary_kept.id: "TRUE_POSITIVE"},
            skipped=[
                SkippedFinding(finding=fallback_kept, reason=SkipReason.OVERSIZED)
            ],
        )
        round_two_prep = analyser.finalise(
            prepare_result.state, [primary_result], OUTPUT_SCHEMA
        )
        assert isinstance(round_two_prep, PrepareResult)

        # Round 2
        assert isinstance(round_two_prep.requests[0], LLMRequest)
        fallback_request = cast(
            LLMRequest[ProcessingPurposeIndicatorModel], round_two_prep.requests[0]
        )
        fallback_result = _build_llm_dispatch_result(
            fallback_request,
            verdicts={fallback_kept.id: "TRUE_POSITIVE"},
        )
        finalise_outcome = analyser.finalise(
            round_two_prep.state, [fallback_result], OUTPUT_SCHEMA
        )
        assert isinstance(finalise_outcome, tuple)
        final, sidecars = finalise_outcome
        assert isinstance(final, Message)
        # Both rounds verdicted TRUE_POSITIVE → no removals → no audit content
        assert sidecars == []
        findings_by_id = {f["id"]: f for f in final.content["findings"]}
        # Primary-validated finding carries marker
        assert (
            findings_by_id[primary_kept.id]["metadata"]["context"].get(
                "processing_purpose_llm_validated"
            )
            is True
        )
        # Fallback-validated finding also carries marker
        assert (
            findings_by_id[fallback_kept.id]["metadata"]["context"].get(
                "processing_purpose_llm_validated"
            )
            is True
        )


# =============================================================================
# Deserialise
# =============================================================================


class TestDeserialise:
    """Tests for deserialise_prepare_result() round-trip fidelity."""

    def test_round_trip_with_llm_request_standard_input(self) -> None:
        """prepare() → model_dump → deserialise → equivalent state and request."""
        analyser = _make_analyser()
        message = _make_standard_input_purpose_message()

        original = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        raw: dict[str, Any] = original.model_dump(mode="json")
        restored = analyser.deserialise_prepare_result(raw)

        assert isinstance(restored.state, ProcessingPurposePrepareState)
        assert restored.state.run_id == original.state.run_id
        assert restored.state.llm_enabled == original.state.llm_enabled
        assert restored.state.input_schema_name == original.state.input_schema_name
        assert len(restored.state.all_findings) == len(original.state.all_findings)
        assert isinstance(restored.state.orchestrator_state, OrchestratorPrepareState)
        assert restored.state.orchestrator_state.run_id == RUN_ID

        assert len(restored.requests) == len(original.requests)
        original_llm_request = original.requests[0]
        restored_llm_request = restored.requests[0]
        assert isinstance(original_llm_request, LLMRequest)
        assert isinstance(restored_llm_request, LLMRequest)
        assert restored_llm_request.batching_mode == original_llm_request.batching_mode
        assert restored_llm_request.run_id == original_llm_request.run_id

    def test_round_trip_with_llm_request_source_code(self) -> None:
        """Source_code round-trip preserves strategy_state inside orchestrator_state."""
        analyser = _make_analyser()
        message = _make_source_code_message_with_purposes()

        original = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        raw: dict[str, Any] = original.model_dump(mode="json")
        restored = analyser.deserialise_prepare_result(raw)

        assert restored.state.input_schema_name == "source_code"
        assert restored.state.orchestrator_state is not None
        assert original.state.orchestrator_state is not None
        # strategy_state (source_contents) survives the round trip
        assert (
            restored.state.orchestrator_state.strategy_state
            == original.state.orchestrator_state.strategy_state
        )

    def test_round_trip_without_llm_request(self) -> None:
        """LLM disabled → orchestrator_state=None, no requests."""
        analyser = _make_analyser(enable_llm=False)
        message = _make_standard_input_purpose_message()

        original = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        raw: dict[str, Any] = original.model_dump(mode="json")
        restored = analyser.deserialise_prepare_result(raw)

        assert restored.requests == []
        assert restored.state.orchestrator_state is None
        assert restored.state.llm_enabled is False

    def test_round_trip_of_between_rounds_state(self) -> None:
        """Between-rounds state (is_fallback_round=True, primary_outcome set) survives JSON."""
        analyser = _make_analyser()
        message = _make_source_code_message_with_purposes()

        prepare_result = analyser.prepare(inputs=[message], output_schema=OUTPUT_SCHEMA)
        assert prepare_result.state.orchestrator_state is not None
        sampled = prepare_result.state.orchestrator_state.strategy_findings
        assert len(sampled) >= 2

        # Produce a between-rounds PrepareResult (OVERSIZED triggers fallback)
        assert isinstance(prepare_result.requests[0], LLMRequest)
        primary_request = cast(
            LLMRequest[ProcessingPurposeIndicatorModel], prepare_result.requests[0]
        )
        primary_result = _build_llm_dispatch_result(
            primary_request,
            verdicts={sampled[1].id: "TRUE_POSITIVE"},
            skipped=[SkippedFinding(finding=sampled[0], reason=SkipReason.OVERSIZED)],
        )
        round_two_prep = analyser.finalise(
            prepare_result.state, [primary_result], OUTPUT_SCHEMA
        )
        assert isinstance(round_two_prep, PrepareResult)

        raw: dict[str, Any] = round_two_prep.model_dump(mode="json")
        restored = analyser.deserialise_prepare_result(raw)

        assert restored.state.orchestrator_state is not None
        assert restored.state.orchestrator_state.is_fallback_round is True
        assert restored.state.orchestrator_state.primary_outcome is not None
        # Fallback strategy_findings preserved
        assert [f.id for f in restored.state.orchestrator_state.strategy_findings] == [
            sampled[0].id
        ]
        # Fallback request preserved
        assert len(restored.requests) == 1
        assert restored.requests[0].request_id == round_two_prep.requests[0].request_id
