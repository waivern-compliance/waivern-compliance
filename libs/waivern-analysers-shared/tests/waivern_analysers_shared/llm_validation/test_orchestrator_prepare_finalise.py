"""Tests for ValidationOrchestrator's prepare() and finalise() methods.

Business behaviour: The orchestrator's prepare/finalise split enables the
executor-driven dispatch pattern. prepare() builds an LLMRequest without
making LLM calls; finalise() interprets dispatch results and applies
group-level decisions. Fallback is handled via multi-round dispatch.
"""

from unittest.mock import Mock

from waivern_core.schemas.finding_types import (
    BaseFindingEvidence,
    BaseFindingMetadata,
    BaseFindingModel,
    PatternMatchDetail,
)
from waivern_core.types import JsonValue
from waivern_llm import LLMDispatchResult, LLMRequest, SkippedFinding, SkipReason

from waivern_analysers_shared.llm_validation.models import (
    LLMValidationOutcome,
    ValidationResult,
)
from waivern_analysers_shared.llm_validation.sampling import SamplingResult
from waivern_analysers_shared.llm_validation.validation_orchestrator import (
    FallbackNeeded,
    OrchestratorPrepareState,
    ValidationOrchestrator,
)
from waivern_analysers_shared.types import LLMValidationConfig


class _Finding(BaseFindingModel[BaseFindingMetadata]):
    """Simple finding with a group attribute for orchestrator tests."""

    group: str


def _make_finding(finding_id: str, group: str = "G") -> _Finding:
    return _Finding(
        id=finding_id,
        group=group,
        evidence=[BaseFindingEvidence(content=f"Evidence for {finding_id}")],
        matched_patterns=[PatternMatchDetail(pattern="test_pattern", match_count=1)],
        metadata=BaseFindingMetadata(source="test_source"),
    )


def _make_config() -> LLMValidationConfig:
    return LLMValidationConfig(enable_llm_validation=True)


class _GroupingByAttr:
    """Grouping strategy keyed on the `group` attribute."""

    @property
    def concern_key(self) -> str:
        return "group"

    def group(self, findings: list[_Finding]) -> dict[str, list[_Finding]]:
        groups: dict[str, list[_Finding]] = {}
        for finding in findings:
            groups.setdefault(finding.group, []).append(finding)
        return groups


class _FixedSampling:
    """Sampling strategy returning preconfigured sampled/non_sampled."""

    def __init__(
        self,
        sampled: dict[str, list[_Finding]],
        non_sampled: dict[str, list[_Finding]],
    ) -> None:
        self._sampled = sampled
        self._non_sampled = non_sampled

    def sample(self, groups: dict[str, list[_Finding]]) -> SamplingResult[_Finding]:
        return SamplingResult(sampled=self._sampled, non_sampled=self._non_sampled)


_TEST_RUN_ID = "test-run-id"


def _make_prepare_mock(
    request: LLMRequest[_Finding] | None,
    strategy_findings_override: list[_Finding] | None = None,
) -> Mock:
    """Mock LLMValidationStrategy whose prepare_validation returns fixed values.

    By default the strategy echoes its received findings; pass
    strategy_findings_override to return a different list.
    """
    strategy = Mock()

    def _prepare(
        findings: list[_Finding],
        config: LLMValidationConfig,
        run_id: str,
    ) -> tuple[list[_Finding], LLMRequest[_Finding] | None]:
        return (strategy_findings_override or findings, request)

    strategy.prepare_validation.side_effect = _prepare
    return strategy


def _dispatch_result(
    request_id: str = "test-request",
    responses: list[dict[str, JsonValue]] | None = None,
    skipped: list[SkippedFinding[_Finding]] | None = None,
) -> LLMDispatchResult:
    """Build an LLMDispatchResult with sensible defaults for tests."""
    return LLMDispatchResult(
        request_id=request_id,
        model_name="test-model",
        responses=responses or [],
        skipped=list(skipped) if skipped else [],
    )


def _make_finalise_strategy(
    outcome: LLMValidationOutcome[_Finding],
) -> Mock:
    """Mock strategy whose finalise_validation returns a fixed outcome."""
    strategy = Mock()
    strategy.finalise_validation.return_value = outcome
    return strategy


class TestOrchestratorPrepare:
    """Tests for ValidationOrchestrator.prepare()."""

    def test_prepare_returns_no_request_for_empty_findings(self) -> None:
        """Empty input -> state with no LLMRequest."""
        strategy = _make_prepare_mock(request=Mock(spec=LLMRequest))
        orchestrator = ValidationOrchestrator(llm_strategy=strategy)

        state, request = orchestrator.prepare([], _make_config(), _TEST_RUN_ID)

        assert request is None
        assert state.strategy_findings == []
        assert state.groups is None
        assert state.sampled is None
        assert state.non_sampled is None
        assert state.is_fallback_round is False
        strategy.prepare_validation.assert_not_called()

    def test_prepare_without_grouping_delegates_to_strategy(self) -> None:
        """No grouping -> all findings passed to strategy.prepare_validation()."""
        findings = [_make_finding("1"), _make_finding("2")]
        sentinel_request = Mock(spec=LLMRequest)
        strategy = _make_prepare_mock(request=sentinel_request)
        orchestrator = ValidationOrchestrator(llm_strategy=strategy)

        state, request = orchestrator.prepare(findings, _make_config(), _TEST_RUN_ID)

        assert request is sentinel_request
        strategy.prepare_validation.assert_called_once_with(
            findings, _make_config(), _TEST_RUN_ID
        )
        assert state.strategy_findings == findings
        assert state.groups is None

    def test_prepare_with_grouping_and_sampling(self) -> None:
        """Groups -> samples -> flattens -> passes samples to strategy."""
        a1 = _make_finding("a1", "GroupA")
        a2 = _make_finding("a2", "GroupA")
        b1 = _make_finding("b1", "GroupB")
        b2 = _make_finding("b2", "GroupB")
        findings = [a1, a2, b1, b2]
        sentinel_request = Mock(spec=LLMRequest)
        strategy = _make_prepare_mock(request=sentinel_request)
        sampling = _FixedSampling(
            sampled={"GroupA": [a1], "GroupB": [b1]},
            non_sampled={"GroupA": [a2], "GroupB": [b2]},
        )

        orchestrator = ValidationOrchestrator(
            llm_strategy=strategy,
            grouping_strategy=_GroupingByAttr(),
            sampling_strategy=sampling,
        )

        state, request = orchestrator.prepare(findings, _make_config(), _TEST_RUN_ID)

        assert request is sentinel_request
        # Only sampled findings are sent to strategy (flattened)
        (passed_findings, _config, _run) = strategy.prepare_validation.call_args.args
        assert sorted(f.id for f in passed_findings) == ["a1", "b1"]
        assert state.strategy_findings == passed_findings

    def test_prepare_state_captures_groups_and_samples(self) -> None:
        """OrchestratorPrepareState has correct groups/sampled/non_sampled."""
        a1 = _make_finding("a1", "GroupA")
        a2 = _make_finding("a2", "GroupA")
        b1 = _make_finding("b1", "GroupB")
        findings = [a1, a2, b1]
        strategy = _make_prepare_mock(request=Mock(spec=LLMRequest))
        sampling = _FixedSampling(
            sampled={"GroupA": [a1], "GroupB": [b1]},
            non_sampled={"GroupA": [a2], "GroupB": []},
        )

        orchestrator = ValidationOrchestrator(
            llm_strategy=strategy,
            grouping_strategy=_GroupingByAttr(),
            sampling_strategy=sampling,
        )

        state, _ = orchestrator.prepare(findings, _make_config(), _TEST_RUN_ID)

        assert state.groups == {"GroupA": [a1, a2], "GroupB": [b1]}
        assert state.sampled == {"GroupA": [a1], "GroupB": [b1]}
        assert state.non_sampled == {"GroupA": [a2], "GroupB": []}


class TestOrchestratorFinalise:
    """Tests for ValidationOrchestrator.finalise()."""

    def test_finalise_without_grouping_returns_validation_result(self) -> None:
        """Ungrouped path -> ValidationResult with correct kept/removed."""
        kept = _make_finding("k")
        removed = _make_finding("r")
        strategy = _make_finalise_strategy(
            LLMValidationOutcome(
                llm_validated_kept=[kept],
                llm_validated_removed=[removed],
                llm_not_flagged=[],
                skipped=[],
            )
        )
        orchestrator = ValidationOrchestrator(llm_strategy=strategy)
        state = OrchestratorPrepareState(
            strategy_findings=[kept, removed],
            config=_make_config(),
            run_id=_TEST_RUN_ID,
        )

        result = orchestrator.finalise(state, _dispatch_result())

        assert isinstance(result, ValidationResult)
        assert result.kept_findings == [kept]
        assert result.removed_findings == [removed]
        assert result.removed_groups == []
        assert result.all_succeeded is True

    def test_finalise_with_grouping_applies_group_decisions(self) -> None:
        """Grouped path -> group decisions (Case A/B/C) applied correctly."""
        # GroupA: all samples FALSE_POSITIVE -> whole group removed
        # GroupB: all kept -> whole group kept
        a1 = _make_finding("a1", "GroupA")
        a2_unsampled = _make_finding("a2", "GroupA")
        b1 = _make_finding("b1", "GroupB")
        b2_unsampled = _make_finding("b2", "GroupB")

        strategy = _make_finalise_strategy(
            LLMValidationOutcome(
                llm_validated_kept=[b1],
                llm_validated_removed=[a1],
                llm_not_flagged=[],
                skipped=[],
            )
        )
        orchestrator = ValidationOrchestrator(
            llm_strategy=strategy,
            grouping_strategy=_GroupingByAttr(),
        )
        state = OrchestratorPrepareState(
            strategy_findings=[a1, b1],
            config=_make_config(),
            run_id=_TEST_RUN_ID,
            groups={"GroupA": [a1, a2_unsampled], "GroupB": [b1, b2_unsampled]},
            sampled={"GroupA": [a1], "GroupB": [b1]},
            non_sampled={"GroupA": [a2_unsampled], "GroupB": [b2_unsampled]},
        )

        result = orchestrator.finalise(state, _dispatch_result())

        assert isinstance(result, ValidationResult)
        # GroupA fully removed; GroupB fully kept
        assert {f.id for f in result.removed_findings} == {"a1", "a2"}
        assert {f.id for f in result.kept_findings} == {"b1", "b2"}
        assert len(result.removed_groups) == 1
        assert result.removed_groups[0].concern_value == "GroupA"

    def test_finalise_applies_marker(self) -> None:
        """Marker callback applied to validated findings, not skipped."""
        validated = _make_finding("v")
        skipped_finding = _make_finding("s")
        strategy = _make_finalise_strategy(
            LLMValidationOutcome(
                llm_validated_kept=[validated],
                llm_validated_removed=[],
                llm_not_flagged=[],
                skipped=[
                    SkippedFinding(
                        finding=skipped_finding, reason=SkipReason.BATCH_ERROR
                    )
                ],
            )
        )
        orchestrator = ValidationOrchestrator(llm_strategy=strategy)
        state = OrchestratorPrepareState(
            strategy_findings=[validated, skipped_finding],
            config=_make_config(),
            run_id=_TEST_RUN_ID,
        )

        def _mark(f: _Finding) -> _Finding:
            return f.model_copy(update={"group": "MARKED"})

        result = orchestrator.finalise(state, _dispatch_result(), marker=_mark)

        assert isinstance(result, ValidationResult)
        # Conservative semantics: skipped findings are kept in output (not dropped)
        kept_by_id = {f.id: f for f in result.kept_findings}
        assert set(kept_by_id) == {"v", "s"}
        # Marker applied to validated finding only
        assert kept_by_id["v"].group == "MARKED"
        # Skipped finding is NOT marked (never went through LLM)
        assert kept_by_id["s"].group == "G"
        # Skipped finding also appears in skipped_samples for transparency
        assert [s.finding.id for s in result.skipped_samples] == ["s"]


class TestOrchestratorFinaliseFallback:
    """Tests for the multi-round fallback mechanism in finalise()."""

    def test_finalise_returns_fallback_needed_for_eligible_skipped(self) -> None:
        """Eligible skipped -> FallbackNeeded with fallback LLMRequest."""
        validated = _make_finding("v")
        oversized = _make_finding("o")
        primary_outcome = LLMValidationOutcome(
            llm_validated_kept=[validated],
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[SkippedFinding(finding=oversized, reason=SkipReason.OVERSIZED)],
        )
        primary_strategy = _make_finalise_strategy(primary_outcome)
        fallback_request = Mock(spec=LLMRequest)
        fallback_strategy = _make_prepare_mock(request=fallback_request)
        orchestrator = ValidationOrchestrator(
            llm_strategy=primary_strategy,
            fallback_strategy=fallback_strategy,
        )
        state = OrchestratorPrepareState(
            strategy_findings=[validated, oversized],
            config=_make_config(),
            run_id=_TEST_RUN_ID,
        )

        returned = orchestrator.finalise(state, _dispatch_result())

        assert isinstance(returned, FallbackNeeded)
        assert returned.request is fallback_request
        assert returned.state.is_fallback_round is True
        assert returned.state.primary_outcome == primary_outcome
        # Only the eligible skipped finding is sent to fallback
        (fallback_findings, _config, _run) = (
            fallback_strategy.prepare_validation.call_args.args
        )
        assert [f.id for f in fallback_findings] == ["o"]
        assert [f.id for f in returned.state.strategy_findings] == ["o"]

    def test_finalise_completes_fallback_round(self) -> None:
        """Round 2 (is_fallback_round=True) -> merged ValidationResult."""
        validated = _make_finding("v")
        oversized = _make_finding("o")
        primary_outcome = LLMValidationOutcome(
            llm_validated_kept=[validated],
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[SkippedFinding(finding=oversized, reason=SkipReason.OVERSIZED)],
        )
        # Fallback succeeds: oversized now validated as kept
        fallback_outcome = LLMValidationOutcome(
            llm_validated_kept=[oversized],
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[],
        )
        # Primary strategy unused in round 2 — only fallback's finalise runs
        primary_strategy = Mock()
        fallback_strategy = _make_finalise_strategy(fallback_outcome)
        orchestrator = ValidationOrchestrator(
            llm_strategy=primary_strategy,
            fallback_strategy=fallback_strategy,
        )
        round_two_state = OrchestratorPrepareState(
            strategy_findings=[oversized],
            config=_make_config(),
            run_id=_TEST_RUN_ID,
            primary_outcome=primary_outcome,
            is_fallback_round=True,
        )

        result = orchestrator.finalise(round_two_state, _dispatch_result())

        assert isinstance(result, ValidationResult)
        assert {f.id for f in result.kept_findings} == {"v", "o"}
        assert result.skipped_samples == []
        assert result.all_succeeded is True
        fallback_strategy.finalise_validation.assert_called_once()
        primary_strategy.finalise_validation.assert_not_called()

    def test_finalise_no_fallback_when_no_eligible_skipped(self) -> None:
        """Fallback configured but no eligible skipped -> ValidationResult directly."""
        validated = _make_finding("v")
        batch_errored = _make_finding("b")
        primary_outcome = LLMValidationOutcome(
            llm_validated_kept=[validated],
            llm_validated_removed=[],
            llm_not_flagged=[],
            # BATCH_ERROR is NOT in FALLBACK_ELIGIBLE_SKIP_REASONS
            skipped=[
                SkippedFinding(finding=batch_errored, reason=SkipReason.BATCH_ERROR)
            ],
        )
        primary_strategy = _make_finalise_strategy(primary_outcome)
        fallback_strategy = _make_prepare_mock(request=Mock(spec=LLMRequest))
        orchestrator = ValidationOrchestrator(
            llm_strategy=primary_strategy,
            fallback_strategy=fallback_strategy,
        )
        state = OrchestratorPrepareState(
            strategy_findings=[validated, batch_errored],
            config=_make_config(),
            run_id=_TEST_RUN_ID,
        )

        result = orchestrator.finalise(state, _dispatch_result())

        assert isinstance(result, ValidationResult)
        fallback_strategy.prepare_validation.assert_not_called()
        assert [s.finding.id for s in result.skipped_samples] == ["b"]

    def test_finalise_no_fallback_when_strategy_not_configured(self) -> None:
        """No fallback strategy -> ValidationResult directly even with skipped."""
        validated = _make_finding("v")
        oversized = _make_finding("o")
        primary_outcome = LLMValidationOutcome(
            llm_validated_kept=[validated],
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[SkippedFinding(finding=oversized, reason=SkipReason.OVERSIZED)],
        )
        primary_strategy = _make_finalise_strategy(primary_outcome)
        orchestrator = ValidationOrchestrator(llm_strategy=primary_strategy)
        state = OrchestratorPrepareState(
            strategy_findings=[validated, oversized],
            config=_make_config(),
            run_id=_TEST_RUN_ID,
        )

        result = orchestrator.finalise(state, _dispatch_result())

        assert isinstance(result, ValidationResult)
        assert [s.finding.id for s in result.skipped_samples] == ["o"]
