"""Tests for ValidationOrchestrator's prepare() and finalise() methods.

Business behaviour: The orchestrator's prepare/finalise split enables the
executor-driven dispatch pattern. prepare() builds an LLMRequest without
making LLM calls; finalise() interprets dispatch results and applies
group-level decisions. Fallback is handled via multi-round dispatch.
"""

from unittest.mock import Mock

import pytest
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
    RemovedItem,
    ValidationResult,
)
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
    # Default to None — tests that need a specific strategy_state override explicitly.
    strategy.export_persistence_state.return_value = None
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

    def test_prepare_with_grouping_and_sampling(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Groups -> samples -> flattens -> passes samples to strategy."""
        a1 = _make_finding("a1", "GroupA")
        a2 = _make_finding("a2", "GroupA")
        b1 = _make_finding("b1", "GroupB")
        b2 = _make_finding("b2", "GroupB")
        findings = [a1, a2, b1, b2]
        sentinel_request = Mock(spec=LLMRequest)
        strategy = _make_prepare_mock(request=sentinel_request)

        # Control randomness: always pick first item from each group
        monkeypatch.setattr("random.sample", lambda items, k: items[:k])

        orchestrator = ValidationOrchestrator(
            llm_strategy=strategy,
            grouping_strategy=_GroupingByAttr(),
            sample_size=1,
        )

        state, request = orchestrator.prepare(findings, _make_config(), _TEST_RUN_ID)

        assert request is sentinel_request
        # Only sampled findings are sent to strategy (flattened)
        (passed_findings, _config, _run) = strategy.prepare_validation.call_args.args
        assert sorted(f.id for f in passed_findings) == ["a1", "b1"]
        assert state.strategy_findings == passed_findings

    def test_prepare_state_captures_groups_and_samples(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """OrchestratorPrepareState has correct groups/sampled/non_sampled."""
        a1 = _make_finding("a1", "GroupA")
        a2 = _make_finding("a2", "GroupA")
        b1 = _make_finding("b1", "GroupB")
        findings = [a1, a2, b1]
        strategy = _make_prepare_mock(request=Mock(spec=LLMRequest))

        # Control randomness: always pick first item from each group
        monkeypatch.setattr("random.sample", lambda items, k: items[:k])

        orchestrator = ValidationOrchestrator(
            llm_strategy=strategy,
            grouping_strategy=_GroupingByAttr(),
            sample_size=1,
        )

        state, _ = orchestrator.prepare(findings, _make_config(), _TEST_RUN_ID)

        assert state.groups == {"GroupA": [a1, a2], "GroupB": [b1]}
        assert state.sampled == {"GroupA": [a1], "GroupB": [b1]}
        assert state.non_sampled == {"GroupA": [a2], "GroupB": []}

    def test_prepare_captures_strategy_persistence_state(self) -> None:
        """Strategy that overrides export_persistence_state() -> captured in state."""
        findings = [_make_finding("1")]
        marker_state: dict[str, JsonValue] = {"marker": "x", "value": 42}
        strategy = _make_prepare_mock(request=Mock(spec=LLMRequest))
        strategy.export_persistence_state.return_value = marker_state
        orchestrator = ValidationOrchestrator(llm_strategy=strategy)

        state, _ = orchestrator.prepare(findings, _make_config(), _TEST_RUN_ID)

        assert state.strategy_state == marker_state

    def test_prepare_state_strategy_state_is_none_for_default_strategies(self) -> None:
        """Strategy using the default export_persistence_state() -> state.strategy_state is None."""
        findings = [_make_finding("1")]
        strategy = _make_prepare_mock(request=Mock(spec=LLMRequest))
        strategy.export_persistence_state.return_value = None
        orchestrator = ValidationOrchestrator(llm_strategy=strategy)

        state, _ = orchestrator.prepare(findings, _make_config(), _TEST_RUN_ID)

        assert state.strategy_state is None

    def test_orchestrator_prepare_state_round_trips_with_strategy_state(self) -> None:
        """OrchestratorPrepareState.strategy_state survives model_dump -> model_validate."""
        original = OrchestratorPrepareState[_Finding](
            strategy_findings=[_make_finding("f1")],
            config=_make_config(),
            run_id=_TEST_RUN_ID,
            strategy_state={
                "source_contents": {"a.py": "content_a", "b.py": "content_b"},
                "nested": {"flag": True, "values": [1, 2, 3]},
            },
        )

        raw: dict[str, JsonValue] = original.model_dump(mode="json")
        restored = OrchestratorPrepareState[_Finding].model_validate(raw)

        assert restored.strategy_state == original.strategy_state

    def test_sample_size_without_grouping_raises(self) -> None:
        """sample_size without grouping_strategy should raise ValueError."""
        strategy = _make_prepare_mock(request=Mock(spec=LLMRequest))

        with pytest.raises(ValueError, match="sample_size requires grouping_strategy"):
            ValidationOrchestrator(
                llm_strategy=strategy,
                sample_size=3,
            )


class TestOrchestratorFinalise:
    """Tests for ValidationOrchestrator.finalise()."""

    def test_finalise_without_grouping_returns_validation_result(self) -> None:
        """Ungrouped path -> ValidationResult propagates RemovedItem reasons from the strategy outcome."""
        kept = _make_finding("k")
        removed = _make_finding("r")
        removed_item = RemovedItem(
            finding=removed, reason="LLM marked as false positive"
        )
        strategy = _make_finalise_strategy(
            LLMValidationOutcome(
                llm_validated_kept=[kept],
                llm_validated_removed=[removed_item],
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
        assert result.removed_findings == [removed_item]
        assert result.removed_findings[0].finding == removed
        assert result.removed_findings[0].reason == "LLM marked as false positive"
        assert result.removed_groups == []
        assert result.all_succeeded is True

    def test_finalise_with_grouping_applies_group_decisions(self) -> None:
        """Grouped Case A removes all members; sampled FPs keep LLM reasons, cascade members get 'Inferred —' reasons.

        Case C is implicit: GroupB has no validated FPs, so it contributes
        nothing to ``removed_findings`` and is fully kept.
        """
        # GroupA: all samples FALSE_POSITIVE -> whole group removed
        # GroupB: all kept -> whole group kept
        a1 = _make_finding("a1", "GroupA")
        a2_unsampled = _make_finding("a2", "GroupA")
        b1 = _make_finding("b1", "GroupB")
        b2_unsampled = _make_finding("b2", "GroupB")

        a1_removed = RemovedItem(finding=a1, reason="LLM said FP for a1")
        strategy = _make_finalise_strategy(
            LLMValidationOutcome(
                llm_validated_kept=[b1],
                llm_validated_removed=[a1_removed],
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
        assert {item.finding.id for item in result.removed_findings} == {"a1", "a2"}
        assert {f.id for f in result.kept_findings} == {"b1", "b2"}
        assert len(result.removed_groups) == 1
        assert result.removed_groups[0].concern_value == "GroupA"

        # Reason provenance: sampled FP keeps its LLM-direct reason; cascade
        # member (a2_unsampled) gets a synthesised 'Inferred —' reason
        # referencing the concern key and value.
        by_id = {item.finding.id: item for item in result.removed_findings}
        assert by_id["a1"].reason == "LLM said FP for a1"
        assert by_id["a2"].reason.startswith("Inferred —")
        assert "group='GroupA'" in by_id["a2"].reason

    def test_finalise_case_b_partial_keep_in_same_group(self) -> None:
        """Case B (mixed kept + FP samples in same group) -> keep group, remove only FP samples with verbatim LLM reasons.

        Case A removes the whole group when all validated samples are
        FALSE_POSITIVE; Case C keeps the whole group when none are. Case B is
        the middle ground: some samples in the group are validated as
        TRUE_POSITIVE and some as FALSE_POSITIVE, so the group survives but
        the LLM-flagged false positives are filtered out. Non-sampled and
        skipped members of the group remain kept (conservative semantics —
        they weren't validated, so we don't infer anything about them).
        """
        # One group, two sampled findings (one kept, one removed) plus a
        # non-sampled member.
        a1_kept = _make_finding("a1", "GroupA")
        a2_removed = _make_finding("a2", "GroupA")
        a3_unsampled = _make_finding("a3", "GroupA")

        a2_removed_item = RemovedItem(finding=a2_removed, reason="LLM said FP for a2")
        strategy = _make_finalise_strategy(
            LLMValidationOutcome(
                llm_validated_kept=[a1_kept],
                llm_validated_removed=[a2_removed_item],
                llm_not_flagged=[],
                skipped=[],
            )
        )
        orchestrator = ValidationOrchestrator(
            llm_strategy=strategy,
            grouping_strategy=_GroupingByAttr(),
        )
        state = OrchestratorPrepareState(
            strategy_findings=[a1_kept, a2_removed],
            config=_make_config(),
            run_id=_TEST_RUN_ID,
            groups={"GroupA": [a1_kept, a2_removed, a3_unsampled]},
            sampled={"GroupA": [a1_kept, a2_removed]},
            non_sampled={"GroupA": [a3_unsampled]},
        )

        result = orchestrator.finalise(state, _dispatch_result())

        assert isinstance(result, ValidationResult)
        # Only the FP sample is removed, with its LLM-direct reason.
        assert result.removed_findings == [a2_removed_item]
        # The kept-validated and non-sampled members survive in the group.
        assert {f.id for f in result.kept_findings} == {"a1", "a3"}
        # Group was NOT wholesale-removed, so removed_groups stays empty.
        assert result.removed_groups == []

    def test_finalise_empty_findings_short_circuits_with_no_removed(self) -> None:
        """Empty state.strategy_findings -> ValidationResult with no removed findings.

        Guards the explicit short-circuit at the top of finalise(); without
        this guard a downstream change could accidentally invoke the strategy
        on an empty input and produce a non-empty removed list.
        """
        # Strategy is configured but should NEVER be invoked — the empty
        # short-circuit must fire before any strategy call.
        strategy = Mock()
        orchestrator = ValidationOrchestrator(llm_strategy=strategy)
        state = OrchestratorPrepareState[_Finding](
            strategy_findings=[],
            config=_make_config(),
            run_id=_TEST_RUN_ID,
        )

        result = orchestrator.finalise(state, _dispatch_result())

        assert isinstance(result, ValidationResult)
        assert result.removed_findings == []
        assert result.kept_findings == []
        assert result.removed_groups == []
        assert result.samples_validated == 0
        assert result.all_succeeded is True
        strategy.finalise_validation.assert_not_called()

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
        """Round 2 (is_fallback_round=True) -> merged ValidationResult; removed findings from primary and fallback are concatenated with reasons preserved."""
        validated = _make_finding("v")
        oversized = _make_finding("o")
        primary_removed = _make_finding("pr")
        fallback_removed = _make_finding("fr")

        primary_removed_item = RemovedItem(
            finding=primary_removed, reason="primary LLM said FP"
        )
        fallback_removed_item = RemovedItem(
            finding=fallback_removed, reason="fallback LLM said FP"
        )
        primary_outcome = LLMValidationOutcome(
            llm_validated_kept=[validated],
            llm_validated_removed=[primary_removed_item],
            llm_not_flagged=[],
            skipped=[SkippedFinding(finding=oversized, reason=SkipReason.OVERSIZED)],
        )
        # Fallback succeeds: oversized now validated as kept; fallback also
        # flags its own FP.
        fallback_outcome = LLMValidationOutcome(
            llm_validated_kept=[oversized],
            llm_validated_removed=[fallback_removed_item],
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

        # Merged outcome concatenates primary + fallback removed items, each
        # with its origin reason intact.
        assert result.removed_findings == [
            primary_removed_item,
            fallback_removed_item,
        ]

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
