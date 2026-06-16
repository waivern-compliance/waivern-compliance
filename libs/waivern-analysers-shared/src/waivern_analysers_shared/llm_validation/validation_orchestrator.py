"""Validation orchestrator for LLM validation.

Orchestrates the complete validation flow by composing grouping, sampling,
and LLM validation strategies. Applies group-level decisions based on
sample validation results.

Architecture
------------

::

    ┌────────────────────────────────────────────────────────────────┐
    │                  ValidationOrchestrator                        │
    │                                                                │
    │  Composes orthogonal concerns:                                 │
    │  • GroupingStrategy: How to organise findings (optional)       │
    │  • sample_size: How many findings to sample per group          │
    │  • LLMValidationStrategy: How to validate findings via LLM     │
    └────────────────────────────────────────────────────────────────┘

Validation strategies declare batching intent on the ``LLMRequest`` they build:
- COUNT_BASED: Simple count-based batching for evidence-only validation.
- EXTENDED_CONTEXT: Token-aware batching with source content.

The orchestrator handles grouping and sampling; the executor's dispatcher
handles batching and LLM calls.

"""

import random
from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict
from waivern_core import Finding
from waivern_core.types import JsonValue
from waivern_llm import LLMDispatchResult, LLMRequest

from waivern_analysers_shared.llm_validation.decision_engine import (
    ValidationDecisionEngine,
)
from waivern_analysers_shared.llm_validation.grouping import GroupingStrategy
from waivern_analysers_shared.llm_validation.models import (
    FALLBACK_ELIGIBLE_SKIP_REASONS,
    LLMValidationOutcome,
    RemovedGroup,
    RemovedItem,
    SkippedFinding,
    ValidationResult,
)
from waivern_analysers_shared.llm_validation.strategy import LLMValidationStrategy
from waivern_analysers_shared.types import LLMValidationConfig


class OrchestratorPrepareState[T: Finding](BaseModel):
    """State captured by ValidationOrchestrator.prepare() for use in finalise().

    Captures everything finalise() needs to produce the final ValidationResult,
    including fallback round state for multi-round dispatch.

    Implemented as a Pydantic BaseModel so it can be embedded inside a
    processor's ``PrepareResult[S: BaseModel].state`` and round-trip through
    ``model_dump(mode="json")`` on the distributed-processor resume path.
    ``arbitrary_types_allowed`` is required because the ``Finding`` bound is
    a Protocol — concrete BaseModel finding types still validate correctly
    via their own pydantic machinery.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    strategy_findings: list[T]
    """Findings passed to the strategy's prepare_validation()."""

    config: LLMValidationConfig
    """LLM validation configuration for this run."""

    run_id: str
    """Run identifier for cache scoping (needed for fallback prepare)."""

    groups: dict[str, list[T]] | None = None
    """Groups from grouping strategy (None if no grouping)."""

    sampled: dict[str, list[T]] | None = None
    """Sampled findings per group (None if no grouping)."""

    non_sampled: dict[str, list[T]] | None = None
    """Non-sampled findings per group (None if no grouping)."""

    primary_outcome: LLMValidationOutcome[T] | None = None
    """Primary strategy outcome, set between fallback rounds."""

    is_fallback_round: bool = False
    """True when finalise is being called with fallback results."""

    strategy_state: dict[str, JsonValue] | None = None
    """Persisted primary-strategy construction state (opaque to the orchestrator).

    Populated from ``LLMValidationStrategy.export_persistence_state()`` during
    ``prepare()``. Used by the processor's factory to reconstruct strategies on
    the fallback/resume round when the strategy's construction requires inputs
    beyond its injected services (e.g., a source content map held by a
    ``SourceProvider``). Strategies that do not override
    ``export_persistence_state()`` leave this as ``None``.
    """


@dataclass(frozen=True)
class FallbackNeeded[T: Finding]:
    """Signal returned from finalise() when a fallback dispatch round is needed.

    The processor wraps this into a PrepareResult, triggering another
    Phase 2 -> 3 cycle in the executor.
    """

    state: OrchestratorPrepareState[T]
    """Updated state carrying primary_outcome and is_fallback_round=True."""

    request: LLMRequest[T]
    """LLMRequest for the fallback strategy."""


class ValidationOrchestrator[T: Finding]:
    """Orchestrates the complete validation flow for filtering strategies.

    Composes orthogonal concerns:
    - GroupingStrategy: How to organise findings (optional)
    - sample_size: How many findings to sample per group (optional, requires grouping)
    - LLMValidationStrategy: How to batch and call the LLM

    Note: This orchestrator is specific to the **filtering** paradigm where
    strategies return ``LLMValidationOutcome``. For enrichment strategies
    that return different result types, use a different orchestrator.

    Validation flow (driven by the executor's prepare/finalise cycle):
    1. ``prepare()``: group findings -> sample -> flatten -> strategy builds
       an ``LLMRequest``.
    2. Executor dispatches the request and hands results to ``finalise()``.
    3. ``finalise()``: strategy deserialises results into an
       ``LLMValidationOutcome``; the orchestrator applies group-level
       decisions (Case A/B/C) and merges fallback outcomes when needed.

    """

    def __init__(
        self,
        llm_strategy: LLMValidationStrategy[T, LLMValidationOutcome[T]],
        grouping_strategy: GroupingStrategy[T] | None = None,
        sample_size: int | None = None,
        fallback_strategy: LLMValidationStrategy[T, LLMValidationOutcome[T]]
        | None = None,
    ) -> None:
        """Initialise orchestrator with strategies.

        Args:
            llm_strategy: Primary strategy for LLM validation.
            grouping_strategy: Optional strategy for grouping findings.
            sample_size: Max findings to sample per group (requires grouping).
                When None, all grouped findings are validated.
            fallback_strategy: Optional fallback for findings skipped by primary.
                Used when primary strategy cannot validate certain findings (e.g.,
                oversized sources, missing content). Only findings skipped for
                specific reasons are eligible for fallback validation.

        Raises:
            ValueError: If sample_size provided without grouping_strategy.

        """
        if sample_size is not None and grouping_strategy is None:
            raise ValueError("sample_size requires grouping_strategy to be provided")

        self._llm_strategy = llm_strategy
        self._grouping_strategy = grouping_strategy
        self._sample_size = sample_size
        self._fallback_strategy = fallback_strategy

    def prepare(
        self,
        findings: list[T],
        config: LLMValidationConfig,
        run_id: str,
    ) -> tuple[OrchestratorPrepareState[T], LLMRequest[T] | None]:
        """Prepare an LLM request for dispatch without making any LLM calls.

        Orchestrates: group -> sample -> flatten -> strategy.prepare_validation().
        Returns the captured state plus the LLMRequest for the executor to dispatch.

        Args:
            findings: List of findings to validate.
            config: LLM validation configuration.
            run_id: Unique identifier for the current run, used for cache scoping.

        Returns:
            Tuple of (state for finalise, LLMRequest or None if no dispatch needed).

        """
        strategy_state = self._llm_strategy.export_persistence_state()

        if not findings:
            return (
                OrchestratorPrepareState(
                    strategy_findings=[],
                    config=config,
                    run_id=run_id,
                    strategy_state=strategy_state,
                ),
                None,
            )

        if self._grouping_strategy is None:
            strategy_findings, request = self._llm_strategy.prepare_validation(
                findings, config, run_id
            )
            return (
                OrchestratorPrepareState(
                    strategy_findings=strategy_findings,
                    config=config,
                    run_id=run_id,
                    strategy_state=strategy_state,
                ),
                request,
            )

        groups = self._grouping_strategy.group(findings)

        if self._sample_size is not None:
            sampled, non_sampled = self._sample_groups(groups, self._sample_size)
        else:
            sampled = groups
            non_sampled: dict[str, list[T]] = {key: [] for key in groups}

        all_samples = [f for group_samples in sampled.values() for f in group_samples]

        strategy_findings, request = self._llm_strategy.prepare_validation(
            all_samples, config, run_id
        )
        return (
            OrchestratorPrepareState(
                strategy_findings=strategy_findings,
                config=config,
                run_id=run_id,
                groups=groups,
                sampled=sampled,
                non_sampled=non_sampled,
                strategy_state=strategy_state,
            ),
            request,
        )

    def finalise(
        self,
        state: OrchestratorPrepareState[T],
        result: LLMDispatchResult | None,
        marker: Callable[[T], T] | None = None,
    ) -> ValidationResult[T] | FallbackNeeded[T]:
        """Finalise validation from dispatch results.

        Round 1 (primary): interpret primary results, check fallback eligibility.
            - If fallback needed -> returns FallbackNeeded for another round.
            - Otherwise -> applies marker, group decisions -> ValidationResult.
        Round 2 (fallback): merges primary + fallback outcomes, applies marker
            and group decisions -> ValidationResult.

        Args:
            state: State captured by prepare().
            result: Dispatch result for the strategy's LLMRequest, or None.
            marker: Optional callback to mark validated findings.

        Returns:
            ValidationResult when complete, or FallbackNeeded when another round
            of dispatch is required.

        """
        # Empty findings short-circuit (matches prepare with empty input)
        if not state.strategy_findings:
            return ValidationResult(
                kept_findings=[],
                removed_findings=[],
                removed_groups=[],
                samples_validated=0,
                all_succeeded=True,
                skipped_samples=[],
            )

        if state.is_fallback_round:
            outcome = self._run_fallback_round(state, result)
        else:
            outcome = self._run_primary_round(state, result)
            fallback_signal = self._build_fallback_request_if_needed(outcome, state)
            if fallback_signal is not None:
                return fallback_signal

        if marker:
            outcome = outcome.with_marked_findings(marker)

        if state.groups is not None and self._grouping_strategy is not None:
            return self._apply_group_decisions(
                grouping_strategy=self._grouping_strategy,
                groups=state.groups,
                sampled=state.sampled or {},
                non_sampled=state.non_sampled or {},
                outcome=outcome,
            )

        # Ungrouped path: include skipped findings in kept_findings
        # (conservative semantics — see ValidationResult.kept_findings docstring).
        return ValidationResult(
            kept_findings=outcome.kept_findings,
            removed_findings=outcome.llm_validated_removed,
            removed_groups=[],
            samples_validated=len(state.strategy_findings),
            all_succeeded=outcome.validation_succeeded,
            skipped_samples=outcome.skipped,
        )

    def _run_primary_round(
        self,
        state: OrchestratorPrepareState[T],
        result: LLMDispatchResult | None,
    ) -> LLMValidationOutcome[T]:
        """Delegate to the primary strategy's finalise_validation (round 1)."""
        return self._llm_strategy.finalise_validation(state.strategy_findings, result)

    def _run_fallback_round(
        self,
        state: OrchestratorPrepareState[T],
        result: LLMDispatchResult | None,
    ) -> LLMValidationOutcome[T]:
        """Merge fallback outcome into primary outcome (round 2).

        Precondition: ``state.is_fallback_round`` implies the fallback strategy
        and primary outcome were set by ``_build_fallback_request_if_needed``.
        """
        fallback_strategy = self._fallback_strategy
        primary_outcome = state.primary_outcome
        if fallback_strategy is None or primary_outcome is None:
            raise RuntimeError(
                "is_fallback_round=True requires fallback_strategy and "
                "primary_outcome to be set"
            )
        fallback_outcome = fallback_strategy.finalise_validation(
            state.strategy_findings, result
        )
        ineligible_skipped = [
            s
            for s in primary_outcome.skipped
            if s.reason not in FALLBACK_ELIGIBLE_SKIP_REASONS
        ]
        return self._merge_fallback_outcome(
            primary_outcome, fallback_outcome, ineligible_skipped
        )

    def _build_fallback_request_if_needed(
        self,
        primary_outcome: LLMValidationOutcome[T],
        state: OrchestratorPrepareState[T],
    ) -> FallbackNeeded[T] | None:
        """Build a FallbackNeeded signal if eligible skipped findings exist."""
        fallback_strategy = self._fallback_strategy
        if fallback_strategy is None:
            return None

        eligible = [
            s.finding
            for s in primary_outcome.skipped
            if s.reason in FALLBACK_ELIGIBLE_SKIP_REASONS
        ]
        if not eligible:
            return None

        fallback_strategy_findings, fallback_request = (
            fallback_strategy.prepare_validation(eligible, state.config, state.run_id)
        )
        if fallback_request is None:
            return None

        next_state = OrchestratorPrepareState(
            strategy_findings=fallback_strategy_findings,
            config=state.config,
            run_id=state.run_id,
            groups=state.groups,
            sampled=state.sampled,
            non_sampled=state.non_sampled,
            primary_outcome=primary_outcome,
            is_fallback_round=True,
        )
        return FallbackNeeded(state=next_state, request=fallback_request)

    def _merge_fallback_outcome(
        self,
        primary: LLMValidationOutcome[T],
        fallback: LLMValidationOutcome[T],
        ineligible_skipped: list[SkippedFinding[T]],
    ) -> LLMValidationOutcome[T]:
        """Merge fallback validation results into primary outcome.

        Args:
            primary: Original outcome from primary strategy.
            fallback: Outcome from fallback strategy.
            ineligible_skipped: Skipped findings not eligible for fallback.

        Returns:
            New LLMValidationOutcome with merged results.

        """
        return LLMValidationOutcome(
            llm_validated_kept=primary.llm_validated_kept + fallback.llm_validated_kept,
            llm_validated_removed=(
                primary.llm_validated_removed + fallback.llm_validated_removed
            ),
            llm_not_flagged=primary.llm_not_flagged + fallback.llm_not_flagged,
            skipped=ineligible_skipped + fallback.skipped,
        )

    def _apply_group_decisions(
        self,
        grouping_strategy: GroupingStrategy[T],
        groups: dict[str, list[T]],
        sampled: dict[str, list[T]],
        non_sampled: dict[str, list[T]],
        outcome: LLMValidationOutcome[T],
    ) -> ValidationResult[T]:
        """Apply group-level decisions based on LLM validation outcome.

        Cases:
        - Case A: All validated samples FALSE_POSITIVE → remove entire group
        - Case B: Some FALSE_POSITIVE → keep group, remove only FP samples
        - Case C: No FALSE_POSITIVE → keep entire group

        """
        # Build lookup sets for quick membership testing
        kept_ids = {f.id for f in outcome.llm_validated_kept}
        kept_ids.update(f.id for f in outcome.llm_not_flagged)
        removed_items_by_id = {
            item.finding.id: item for item in outcome.llm_validated_removed
        }
        skipped_ids = {s.finding.id for s in outcome.skipped}

        # Build mapping from ID to actual findings from outcome
        # (these may be marked if marker was applied)
        kept_findings_by_id = {f.id: f for f in outcome.llm_validated_kept}
        kept_findings_by_id.update({f.id: f for f in outcome.llm_not_flagged})
        skipped_findings_by_id = {s.finding.id: s.finding for s in outcome.skipped}

        # Accumulators
        all_kept: list[T] = []
        all_removed: list[RemovedItem[T]] = []
        removed_groups: list[RemovedGroup] = []

        for group_key, group_findings in groups.items():
            group_samples = sampled.get(group_key, [])
            group_non_sampled = non_sampled.get(group_key, [])

            # Identify validated samples by category (exclude skipped from decision)
            validated_kept_ids = [f.id for f in group_samples if f.id in kept_ids]
            validated_removed_items = [
                removed_items_by_id[f.id]
                for f in group_samples
                if f.id in removed_items_by_id
            ]
            group_skipped_ids = [f.id for f in group_samples if f.id in skipped_ids]

            # Classify group using decision engine
            decision = ValidationDecisionEngine.classify_group(
                kept_count=len(validated_kept_ids),
                removed_count=len(validated_removed_items),
            )

            match decision:
                case "keep_all":
                    # No validated samples - keep entire group (conservative)
                    all_kept.extend(group_findings)

                case "remove_group":
                    # All validated samples are FALSE_POSITIVE - remove entire group,
                    # including any skipped findings. Rationale: once we are confident
                    # a whole group is false-positive, the skipped members of that
                    # group inherit the group-level judgement. Conservative handling
                    # of skipped findings only applies when the group is NOT removed.
                    #
                    # Sampled FALSE_POSITIVE members keep their LLM-direct reason;
                    # all other members (non-sampled, skipped) inherit a synthesised
                    # cascade reason explaining the inference.
                    sampled_fp_ids = {
                        item.finding.id for item in validated_removed_items
                    }
                    cascade_reason = (
                        f"Inferred — all {len(validated_removed_items)} validated samples in "
                        f"{grouping_strategy.concern_key}='{group_key}' "
                        "were marked FALSE_POSITIVE by LLM"
                    )
                    for finding in group_findings:
                        if finding.id in sampled_fp_ids:
                            all_removed.append(removed_items_by_id[finding.id])
                        else:
                            all_removed.append(
                                RemovedItem(finding=finding, reason=cascade_reason)
                            )
                    removed_groups.append(
                        RemovedGroup(
                            concern_key=grouping_strategy.concern_key,
                            concern_value=group_key,
                            findings_count=len(group_findings),
                            samples_validated=len(validated_kept_ids)
                            + len(validated_removed_items),
                            reason="All validated samples were false positives",
                            require_review=True,
                        )
                    )

                case "keep_partial":
                    # Mixed results - keep group, remove only FP samples
                    # Use findings from outcome (may be marked) for validated samples
                    all_kept.extend(
                        kept_findings_by_id[fid] for fid in validated_kept_ids
                    )
                    # Non-sampled findings are kept as-is (not validated, not marked)
                    all_kept.extend(group_non_sampled)
                    # Skipped findings use original from outcome (not marked)
                    all_kept.extend(
                        skipped_findings_by_id[fid] for fid in group_skipped_ids
                    )
                    # Remove: FALSE_POSITIVE samples (with their LLM-direct reasons)
                    all_removed.extend(validated_removed_items)

        return ValidationResult(
            kept_findings=all_kept,
            removed_findings=all_removed,
            removed_groups=removed_groups,
            samples_validated=len(outcome.llm_validated_kept)
            + len(outcome.llm_validated_removed)
            + len(outcome.llm_not_flagged),
            all_succeeded=outcome.validation_succeeded,
            skipped_samples=outcome.skipped,
        )

    @staticmethod
    def _sample_groups(
        groups: dict[str, list[T]],
        sample_size: int,
    ) -> tuple[dict[str, list[T]], dict[str, list[T]]]:
        """Randomly sample up to ``sample_size`` findings per group.

        Returns:
            Tuple of (sampled, non_sampled) dicts keyed by group.

        """
        sampled: dict[str, list[T]] = {}
        non_sampled: dict[str, list[T]] = {}

        for group_key, findings in groups.items():
            if len(findings) <= sample_size:
                sampled[group_key] = list(findings)
                non_sampled[group_key] = []
            else:
                samples = random.sample(findings, sample_size)
                sampled[group_key] = samples
                sample_ids = {f.id for f in samples}
                non_sampled[group_key] = [f for f in findings if f.id not in sample_ids]

        return sampled, non_sampled
