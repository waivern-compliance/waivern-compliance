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
    │  Composes orthogonal strategies:                               │
    │  • GroupingStrategy: How to organise findings (optional)       │
    │  • SamplingStrategy: How to sample from groups (optional)      │
    │  • LLMValidationStrategy: How to batch and call the LLM ◄──────┼─ Batching
    └────────────────────────────────────────────────────────────────┘
                                  │
              ┌───────────────────┴───────────────────┐
              ▼                                       ▼
    ┌───────────────────────┐           ┌──────────────────────────────┐
    │ DefaultLLMValidation  │           │ ExtendedContextLLMValidation │
    │      Strategy         │           │         Strategy             │
    ├───────────────────────┤           ├──────────────────────────────┤
    │ Count-based batching  │           │ Token-aware source           │
    │ (llm_batch_size)      │           │ batching with content        │
    │                       │           │                              │
    │ Use for: simple       │           │ Use for: validation          │
    │ finding validation    │           │ needing full source          │
    └───────────────────────┘           └──────────────────────────────┘

Batching is a strategy concern, not an orchestrator concern. Each
LLMValidationStrategy implementation chooses its own batching approach:

- **DefaultLLMValidationStrategy**: Simple count-based batching. Batches
  findings by ``llm_batch_size`` regardless of content size.

- **ExtendedContextLLMValidationStrategy**: Token-aware batching. Groups
  findings by source (file, table, etc.) and batches based on token limits
  to fit within model context windows.

"""

from collections.abc import Callable

from waivern_core import Finding
from waivern_llm import BaseLLMService

from waivern_analysers_shared.llm_validation.decision_engine import (
    ValidationDecisionEngine,
)
from waivern_analysers_shared.llm_validation.grouping import GroupingStrategy
from waivern_analysers_shared.llm_validation.models import (
    FALLBACK_ELIGIBLE_SKIP_REASONS,
    LLMValidationOutcome,
    RemovedGroup,
    SkippedFinding,
    ValidationResult,
)
from waivern_analysers_shared.llm_validation.sampling import SamplingStrategy
from waivern_analysers_shared.llm_validation.strategy import LLMValidationStrategy
from waivern_analysers_shared.types import LLMValidationConfig


class ValidationOrchestrator[T: Finding]:
    """Orchestrates the complete validation flow for filtering strategies.

    Composes orthogonal strategies:
    - GroupingStrategy: How to organise findings (optional)
    - SamplingStrategy: How to sample from groups (optional, requires grouping)
    - LLMValidationStrategy: How to batch and call the LLM

    Note: This orchestrator is specific to the **filtering** paradigm where
    strategies return ``LLMValidationOutcome``. For enrichment strategies
    that return different result types, use a different orchestrator.

    Validation flow:
    1. Group findings using GroupingStrategy (if provided)
    2. Sample from groups using SamplingStrategy (if provided)
    3. Flatten all sampled findings into a single list
    4. Validate via llm_strategy.validate_findings()
    5. Match results back to groups by finding ID
    6. Apply group-level decisions (Case A/B/C)

    """

    def __init__(
        self,
        llm_strategy: LLMValidationStrategy[T, LLMValidationOutcome[T]],
        grouping_strategy: GroupingStrategy[T] | None = None,
        sampling_strategy: SamplingStrategy[T] | None = None,
        fallback_strategy: LLMValidationStrategy[T, LLMValidationOutcome[T]]
        | None = None,
    ) -> None:
        """Initialise orchestrator with strategies.

        Args:
            llm_strategy: Primary strategy for LLM validation.
            grouping_strategy: Optional strategy for grouping findings.
            sampling_strategy: Optional strategy for sampling (requires grouping).
            fallback_strategy: Optional fallback for findings skipped by primary.
                Used when primary strategy cannot validate certain findings (e.g.,
                oversized sources, missing content). Only findings skipped for
                specific reasons are eligible for fallback validation.

        Raises:
            ValueError: If sampling_strategy provided without grouping_strategy.

        """
        if sampling_strategy is not None and grouping_strategy is None:
            raise ValueError(
                "sampling_strategy requires grouping_strategy to be provided"
            )

        self._llm_strategy = llm_strategy
        self._grouping_strategy = grouping_strategy
        self._sampling_strategy = sampling_strategy
        self._fallback_strategy = fallback_strategy

    # TODO: Post-migration cleanup (once all processors use LLMService v2):
    #   Remove llm_service parameter - v2 strategies receive LLMService via
    #   constructor injection and ignore this parameter.
    def validate(
        self,
        findings: list[T],
        config: LLMValidationConfig,
        llm_service: BaseLLMService,
        marker: Callable[[T], T] | None = None,
        run_id: str | None = None,
    ) -> ValidationResult[T]:
        """Validate findings using the configured strategies.

        Args:
            findings: List of findings to validate.
            config: LLM validation configuration.
            llm_service: LLM service instance.
            marker: Optional callback to mark validated findings. Called on findings
                that actually went through LLM validation (not skipped/errored).
                Applied at the strategy level before aggregation into ValidationResult.
            run_id: Unique identifier for the current run, used for cache scoping.

        Returns:
            ValidationResult with validated findings and metadata.

        """
        # Empty findings - return empty result
        if not findings:
            return ValidationResult(
                kept_findings=[],
                removed_findings=[],
                removed_groups=[],
                samples_validated=0,
                all_succeeded=True,
                skipped_samples=[],
            )

        # No grouping - direct validation
        if self._grouping_strategy is None:
            return self._validate_without_grouping(
                findings, config, llm_service, marker, run_id
            )

        # With grouping - full orchestration flow
        return self._validate_with_grouping(
            findings, config, llm_service, marker, run_id
        )

    def _validate_without_grouping(
        self,
        findings: list[T],
        config: LLMValidationConfig,
        llm_service: BaseLLMService,
        marker: Callable[[T], T] | None = None,
        run_id: str | None = None,
    ) -> ValidationResult[T]:
        """Validate findings directly without grouping.

        Calls LLM strategy directly, runs fallback if configured and needed,
        then maps outcome to ValidationResult. No group-level decisions apply.

        """
        outcome = self._llm_strategy.validate_findings(
            findings, config, llm_service, run_id
        )

        # Run fallback on eligible skipped findings
        if self._fallback_strategy is not None:
            outcome = self._run_fallback_validation(
                outcome, config, llm_service, run_id
            )

        # Apply marker at strategy level (before aggregation) if provided
        if marker:
            outcome = outcome.with_marked_findings(marker)

        return ValidationResult(
            kept_findings=outcome.llm_validated_kept + outcome.llm_not_flagged,
            removed_findings=outcome.llm_validated_removed,
            removed_groups=[],  # No grouping = no group removal
            samples_validated=len(findings),
            all_succeeded=outcome.validation_succeeded,
            skipped_samples=outcome.skipped,
        )

    def _validate_with_grouping(
        self,
        findings: list[T],
        config: LLMValidationConfig,
        llm_service: BaseLLMService,
        marker: Callable[[T], T] | None = None,
        run_id: str | None = None,
    ) -> ValidationResult[T]:
        """Validate findings with grouping and optional sampling.

        Full orchestration flow:
        1. Group findings
        2. Sample from groups (if sampling strategy provided)
        3. Flatten samples and validate via LLM
        4. Apply marker at strategy level (before aggregation)
        5. Match results back to groups
        6. Apply group-level decisions (Case A/B/C)

        Precondition: self._grouping_strategy is not None (caller verified).
        """
        # Caller ensures _grouping_strategy is not None before calling
        grouping_strategy = self._grouping_strategy
        if grouping_strategy is None:
            raise RuntimeError("Grouping strategy required but not configured")

        # Step 1: Group findings
        groups = grouping_strategy.group(findings)

        # Step 2: Sample from groups (or use all findings as samples)
        if self._sampling_strategy is not None:
            sampling_result = self._sampling_strategy.sample(groups)
            sampled = sampling_result.sampled
            non_sampled = sampling_result.non_sampled
        else:
            # No sampling - all findings are samples, none are non-sampled
            sampled = groups
            non_sampled: dict[str, list[T]] = {}

        # Step 3: Flatten samples for single LLM call
        all_samples = [f for group_samples in sampled.values() for f in group_samples]

        if not all_samples:
            # No samples to validate - keep all findings
            return ValidationResult(
                kept_findings=findings,
                removed_findings=[],
                removed_groups=[],
                samples_validated=0,
                all_succeeded=True,
                skipped_samples=[],
            )

        # Step 4: Validate samples via LLM
        outcome = self._llm_strategy.validate_findings(
            all_samples, config, llm_service, run_id
        )

        # Step 4b: Run fallback on eligible skipped findings
        if self._fallback_strategy is not None:
            outcome = self._run_fallback_validation(
                outcome, config, llm_service, run_id
            )

        # Step 5: Apply marker at strategy level (before aggregation) if provided
        if marker:
            outcome = outcome.with_marked_findings(marker)

        # Step 6: Apply group-level decisions
        return self._apply_group_decisions(
            grouping_strategy=grouping_strategy,
            groups=groups,
            sampled=sampled,
            non_sampled=non_sampled,
            outcome=outcome,
        )

    def _run_fallback_validation(
        self,
        primary_outcome: LLMValidationOutcome[T],
        config: LLMValidationConfig,
        llm_service: BaseLLMService,
        run_id: str | None = None,
    ) -> LLMValidationOutcome[T]:
        """Run fallback validation on eligible skipped findings.

        Orchestrates fallback flow:
        1. Extract findings eligible for fallback (based on skip reason)
        2. If none eligible, return primary outcome unchanged
        3. Run fallback strategy on eligible findings
        4. Merge results back into primary outcome

        Args:
            primary_outcome: Outcome from primary strategy.
            config: LLM validation configuration.
            llm_service: LLM service instance.
            run_id: Unique identifier for the current run, used for cache scoping.

        Returns:
            LLMValidationOutcome with fallback results merged in.

        """
        # Caller ensures _fallback_strategy is not None before calling this method
        fallback_strategy = self._fallback_strategy
        if fallback_strategy is None:
            return primary_outcome

        # Extract findings eligible for fallback
        eligible_for_fallback: list[T] = []
        ineligible_skipped: list[SkippedFinding[T]] = []

        for skipped in primary_outcome.skipped:
            if skipped.reason in FALLBACK_ELIGIBLE_SKIP_REASONS:
                eligible_for_fallback.append(skipped.finding)
            else:
                ineligible_skipped.append(skipped)

        # No eligible findings - return unchanged
        if not eligible_for_fallback:
            return primary_outcome

        # Run fallback strategy
        fallback_outcome = fallback_strategy.validate_findings(
            eligible_for_fallback, config, llm_service, run_id
        )

        # Merge results
        return self._merge_fallback_outcome(
            primary_outcome, fallback_outcome, ineligible_skipped
        )

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
        removed_ids = {f.id for f in outcome.llm_validated_removed}
        skipped_ids = {s.finding.id for s in outcome.skipped}

        # Build mapping from ID to actual findings from outcome
        # (these may be marked if marker was applied)
        kept_findings_by_id = {f.id: f for f in outcome.llm_validated_kept}
        kept_findings_by_id.update({f.id: f for f in outcome.llm_not_flagged})
        skipped_findings_by_id = {s.finding.id: s.finding for s in outcome.skipped}

        # Accumulators
        all_kept: list[T] = []
        all_removed: list[T] = []
        removed_groups: list[RemovedGroup] = []

        for group_key, group_findings in groups.items():
            group_samples = sampled.get(group_key, [])
            group_non_sampled = non_sampled.get(group_key, [])

            # Identify validated samples by category (exclude skipped from decision)
            validated_kept_ids = [f.id for f in group_samples if f.id in kept_ids]
            validated_removed = [f for f in group_samples if f.id in removed_ids]
            group_skipped_ids = [f.id for f in group_samples if f.id in skipped_ids]

            # Classify group using decision engine
            decision = ValidationDecisionEngine.classify_group(
                kept_count=len(validated_kept_ids),
                removed_count=len(validated_removed),
            )

            match decision:
                case "keep_all":
                    # No validated samples - keep entire group (conservative)
                    all_kept.extend(group_findings)

                case "remove_group":
                    # All validated samples are FALSE_POSITIVE - remove entire group
                    all_removed.extend(group_findings)
                    removed_groups.append(
                        RemovedGroup(
                            concern_key=grouping_strategy.concern_key,
                            concern_value=group_key,
                            findings_count=len(group_findings),
                            samples_validated=len(validated_kept_ids)
                            + len(validated_removed),
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
                    # Remove: FALSE_POSITIVE samples
                    all_removed.extend(validated_removed)

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
