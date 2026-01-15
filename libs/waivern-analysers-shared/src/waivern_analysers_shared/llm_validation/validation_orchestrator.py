"""Validation orchestrator for LLM validation.

Orchestrates the complete validation flow by composing grouping, sampling,
and LLM validation strategies. Applies group-level decisions based on
sample validation results.
"""

from waivern_core.schemas import BaseFindingModel
from waivern_llm import BaseLLMService

from waivern_analysers_shared.llm_validation.grouping import GroupingStrategy
from waivern_analysers_shared.llm_validation.models import (
    LLMValidationOutcome,
    RemovedGroup,
    ValidationResult,
)
from waivern_analysers_shared.llm_validation.sampling import SamplingStrategy
from waivern_analysers_shared.llm_validation.strategy import LLMValidationStrategy
from waivern_analysers_shared.types import LLMValidationConfig


class ValidationOrchestrator[T: BaseFindingModel]:
    """Orchestrates the complete validation flow.

    Composes orthogonal strategies:
    - GroupingStrategy: How to organise findings (optional)
    - SamplingStrategy: How to sample from groups (optional, requires grouping)
    - LLMValidationStrategy: How to batch and call the LLM

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
        llm_strategy: LLMValidationStrategy[T],
        grouping_strategy: GroupingStrategy[T] | None = None,
        sampling_strategy: SamplingStrategy[T] | None = None,
    ) -> None:
        """Initialise orchestrator with strategies.

        Args:
            llm_strategy: Strategy for LLM validation.
            grouping_strategy: Optional strategy for grouping findings.
            sampling_strategy: Optional strategy for sampling (requires grouping).

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

    def validate(
        self,
        findings: list[T],
        config: LLMValidationConfig,
        llm_service: BaseLLMService,
    ) -> ValidationResult[T]:
        """Validate findings using the configured strategies.

        Args:
            findings: List of findings to validate.
            config: LLM validation configuration.
            llm_service: LLM service instance.

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
            return self._validate_without_grouping(findings, config, llm_service)

        # With grouping - full orchestration flow
        return self._validate_with_grouping(
            self._grouping_strategy, findings, config, llm_service
        )

    def _validate_without_grouping(
        self,
        findings: list[T],
        config: LLMValidationConfig,
        llm_service: BaseLLMService,
    ) -> ValidationResult[T]:
        """Validate findings directly without grouping.

        Calls LLM strategy directly and maps outcome to ValidationResult.
        No group-level decisions apply.

        """
        outcome = self._llm_strategy.validate_findings(findings, config, llm_service)

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
        grouping_strategy: GroupingStrategy[T],
        findings: list[T],
        config: LLMValidationConfig,
        llm_service: BaseLLMService,
    ) -> ValidationResult[T]:
        """Validate findings with grouping and optional sampling.

        Full orchestration flow:
        1. Group findings
        2. Sample from groups (if sampling strategy provided)
        3. Flatten samples and validate via LLM
        4. Match results back to groups
        5. Apply group-level decisions (Case A/B/C)

        """
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
        outcome = self._llm_strategy.validate_findings(all_samples, config, llm_service)

        # Step 5: Apply group-level decisions
        return self._apply_group_decisions(
            grouping_strategy=grouping_strategy,
            groups=groups,
            sampled=sampled,
            non_sampled=non_sampled,
            outcome=outcome,
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

        # Accumulators
        all_kept: list[T] = []
        all_removed: list[T] = []
        removed_groups: list[RemovedGroup] = []

        for group_key, group_findings in groups.items():
            group_samples = sampled.get(group_key, [])
            group_non_sampled = non_sampled.get(group_key, [])

            # Count validated samples (exclude skipped from decision)
            validated_kept = [f for f in group_samples if f.id in kept_ids]
            validated_removed = [f for f in group_samples if f.id in removed_ids]
            group_skipped = [f for f in group_samples if f.id in skipped_ids]

            # Determine case based on validated samples only
            total_validated = len(validated_kept) + len(validated_removed)

            if total_validated == 0:
                # No validated samples - keep group (conservative)
                all_kept.extend(group_findings)
            elif len(validated_removed) == total_validated:
                # Case A: All validated samples are FALSE_POSITIVE
                all_removed.extend(group_findings)
                removed_groups.append(
                    RemovedGroup(
                        concern_key=grouping_strategy.concern_key,
                        concern_value=group_key,
                        findings_count=len(group_findings),
                        samples_validated=total_validated,
                        reason="All validated samples were false positives",
                        require_review=True,
                    )
                )
            else:
                # Case B or C: Keep group
                # Keep: validated TRUE_POSITIVE samples + non-sampled + skipped samples
                all_kept.extend(validated_kept)
                all_kept.extend(group_non_sampled)
                all_kept.extend(group_skipped)
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
