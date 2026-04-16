"""Tests for FilteringValidationStrategy's default finalise_validation().

Business behaviour: Filtering strategies share identical response-to-outcome
mapping. The default implementation on FilteringValidationStrategy deserialises
raw dispatch responses, categorises findings, and handles skipped findings.
"""

from typing import override

from waivern_core.schemas import (
    BaseFindingEvidence,
    BaseFindingMetadata,
    BaseFindingModel,
    PatternMatchDetail,
)
from waivern_core.types import JsonValue
from waivern_llm import (
    LLMDispatchResult,
    LLMRequest,
    SkippedFinding,
    SkipReason,
)

from waivern_analysers_shared.llm_validation.models import LLMValidationOutcome
from waivern_analysers_shared.llm_validation.strategy import (
    FilteringValidationStrategy,
)
from waivern_analysers_shared.types import LLMValidationConfig

_TestFinding = BaseFindingModel[BaseFindingMetadata]


class _FilteringStrategyForTests(FilteringValidationStrategy[_TestFinding]):
    """Concrete subclass — abstract methods unused by these tests."""

    @override
    def validate_findings(
        self,
        findings: list[_TestFinding],
        config: LLMValidationConfig,
        run_id: str,
    ) -> LLMValidationOutcome[_TestFinding]:
        raise NotImplementedError

    @override
    def prepare_validation(
        self,
        findings: list[_TestFinding],
        config: LLMValidationConfig,
        run_id: str,
    ) -> tuple[list[_TestFinding], LLMRequest[_TestFinding] | None]:
        raise NotImplementedError


def _make_finding(finding_id: str) -> _TestFinding:
    """Create a test finding with a deterministic ID."""
    return BaseFindingModel(
        id=finding_id,
        evidence=[BaseFindingEvidence(content="test content")],
        matched_patterns=[PatternMatchDetail(pattern="test", match_count=1)],
        metadata=BaseFindingMetadata(source="test_source"),
    )


def _response_result(
    finding_id: str,
    validation_result: str = "TRUE_POSITIVE",
    recommended_action: str = "keep",
) -> dict[str, JsonValue]:
    """Build a single raw response result dict."""
    return {
        "finding_id": finding_id,
        "validation_result": validation_result,
        "confidence": 0.9,
        "reasoning": "test reasoning",
        "recommended_action": recommended_action,
    }


def _dispatch_result(
    responses: list[dict[str, JsonValue]],
    skipped: list[SkippedFinding[_TestFinding]] | None = None,
) -> LLMDispatchResult:
    """Build an LLMDispatchResult with sensible defaults for tests."""
    return LLMDispatchResult(
        request_id="test-request",
        model_name="test-model",
        responses=responses,
        skipped=list(skipped) if skipped else [],
    )


class TestDefaultFinaliseValidation:
    """Tests for the default finalise_validation() on FilteringValidationStrategy."""

    def test_deserialises_responses_and_categorises_findings(self) -> None:
        """Raw dict responses -> TRUE_POSITIVE in kept, FALSE_POSITIVE in removed."""
        strategy = _FilteringStrategyForTests()
        kept_finding = _make_finding("kept")
        removed_finding = _make_finding("removed")
        dispatch_result = _dispatch_result(
            responses=[
                {
                    "results": [
                        _response_result("kept", "TRUE_POSITIVE", "keep"),
                        _response_result("removed", "FALSE_POSITIVE", "discard"),
                    ]
                }
            ],
        )

        outcome = strategy.finalise_validation(
            [kept_finding, removed_finding], dispatch_result
        )

        assert outcome.llm_validated_kept == [kept_finding]
        assert outcome.llm_validated_removed == [removed_finding]
        assert outcome.llm_not_flagged == []
        assert outcome.skipped == []

    def test_findings_not_in_responses_are_not_flagged(self) -> None:
        """Findings present in input but absent from LLM responses -> not_flagged."""
        strategy = _FilteringStrategyForTests()
        mentioned = _make_finding("mentioned")
        missing_one = _make_finding("missing_one")
        missing_two = _make_finding("missing_two")
        dispatch_result = _dispatch_result(
            responses=[{"results": [_response_result("mentioned")]}],
        )

        outcome = strategy.finalise_validation(
            [mentioned, missing_one, missing_two], dispatch_result
        )

        assert outcome.llm_validated_kept == [mentioned]
        assert outcome.llm_validated_removed == []
        assert {f.id for f in outcome.llm_not_flagged} == {"missing_one", "missing_two"}
        assert outcome.skipped == []

    def test_matches_skipped_findings_to_typed_findings(self) -> None:
        """SkippedFinding[Finding] from result -> SkippedFinding[TFinding] by ID."""
        strategy = _FilteringStrategyForTests()
        processed = _make_finding("processed")
        skipped_finding = _make_finding("skipped")
        dispatch_result = _dispatch_result(
            responses=[{"results": [_response_result("processed")]}],
            skipped=[
                SkippedFinding(finding=skipped_finding, reason=SkipReason.OVERSIZED)
            ],
        )

        outcome = strategy.finalise_validation(
            [processed, skipped_finding], dispatch_result
        )

        assert outcome.llm_validated_kept == [processed]
        assert outcome.llm_not_flagged == []
        assert len(outcome.skipped) == 1
        assert outcome.skipped[0].finding is skipped_finding
        assert outcome.skipped[0].reason == SkipReason.OVERSIZED

    def test_returns_all_skipped_when_result_is_none(self) -> None:
        """None result -> all findings as SkippedFinding(BATCH_ERROR)."""
        strategy = _FilteringStrategyForTests()
        first = _make_finding("first")
        second = _make_finding("second")

        outcome = strategy.finalise_validation([first, second], None)

        assert outcome.llm_validated_kept == []
        assert outcome.llm_validated_removed == []
        assert outcome.llm_not_flagged == []
        assert len(outcome.skipped) == 2
        assert all(s.reason == SkipReason.BATCH_ERROR for s in outcome.skipped)
        assert {s.finding.id for s in outcome.skipped} == {"first", "second"}


class TestExportPersistenceStateDefault:
    """Tests for the default export_persistence_state() on LLMValidationStrategy."""

    def test_default_returns_none(self) -> None:
        """Strategy that does not override export_persistence_state -> returns None."""
        strategy = _FilteringStrategyForTests()

        assert strategy.export_persistence_state() is None
