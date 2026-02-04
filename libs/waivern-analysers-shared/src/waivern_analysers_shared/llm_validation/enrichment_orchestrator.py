"""Enrichment orchestration for LLM-based finding enrichment.

Orchestrates the flow: group → sample → flatten → call strategy → return result.
Unlike ValidationOrchestrator, this does not make group-level decisions -
the consumer (classifier) interprets the strategy result.
"""

from dataclasses import dataclass
from typing import Protocol

from waivern_core import Finding
from waivern_llm.v2 import SkippedFinding, SkipReason

from waivern_analysers_shared.llm_validation.grouping import GroupingStrategy
from waivern_analysers_shared.llm_validation.sampling import SamplingStrategy
from waivern_analysers_shared.types import LLMValidationConfig


class EnrichmentStrategy[TFinding: Finding, TResult](Protocol):
    """Protocol for enrichment strategies.

    Strategies receive LLMService via constructor injection, not method parameter.
    """

    def enrich(
        self,
        findings: list[TFinding],
        config: LLMValidationConfig,
        run_id: str,
    ) -> TResult:
        """Enrich findings using LLM.

        Args:
            findings: Findings to enrich.
            config: LLM validation configuration.
            run_id: Run ID for cache scoping.

        Returns:
            Strategy-specific result (consumer interprets).

        """
        ...


@dataclass
class EnrichmentResult[TFinding: Finding, TResult]:
    """Result from enrichment orchestration.

    The strategy_result contains the finding→enrichment mapping.
    The classifier extracts enriched finding IDs directly from the result.
    """

    strategy_result: TResult | None
    """Raw result from strategy (contains finding_id → enrichment mapping). None if empty input."""

    all_findings: list[TFinding]
    """All original findings passed to orchestrator."""

    groups: dict[str, list[TFinding]] | None
    """Groups (if grouping used), for propagation decisions."""

    skipped: list[SkippedFinding[TFinding]]
    """Findings that couldn't be enriched."""

    @property
    def all_succeeded(self) -> bool:
        """Whether all findings were enriched without errors."""
        return len(self.skipped) == 0


class EnrichmentOrchestrator[TFinding: Finding, TResult]:
    """Orchestrates enrichment flow: group → sample → enrich.

    Unlike ValidationOrchestrator:
    - Allows sampling without grouping (implicit single group)
    - Does not make Case A/B/C decisions (consumer handles)
    - No fallback strategy or marker callback
    """

    def __init__(
        self,
        enrichment_strategy: EnrichmentStrategy[TFinding, TResult],
        grouping_strategy: GroupingStrategy[TFinding] | None = None,
        sampling_strategy: SamplingStrategy[TFinding] | None = None,
    ) -> None:
        """Initialise with strategies.

        Args:
            enrichment_strategy: Strategy for LLM enrichment.
            grouping_strategy: Optional strategy for grouping findings.
            sampling_strategy: Optional strategy for sampling from groups.

        """
        self._enrichment_strategy = enrichment_strategy
        self._grouping_strategy = grouping_strategy
        self._sampling_strategy = sampling_strategy

    def enrich(
        self,
        findings: list[TFinding],
        config: LLMValidationConfig,
        run_id: str,
    ) -> EnrichmentResult[TFinding, TResult]:
        """Orchestrate enrichment flow.

        Flow:
        1. Group findings (if grouping_strategy provided)
        2. Sample from groups (if sampling_strategy provided)
        3. Flatten samples into single list
        4. Call enrichment_strategy.enrich(samples, ...)
        5. Return EnrichmentResult with strategy result + context

        Args:
            findings: Findings to enrich.
            config: LLM validation configuration.
            run_id: Run ID for cache scoping.

        Returns:
            EnrichmentResult containing strategy result and context.

        """
        # Empty input → empty result, don't call strategy
        if not findings:
            return EnrichmentResult(
                strategy_result=None,
                all_findings=[],
                groups=None,
                skipped=[],
            )

        # Step 1: Group findings (if grouping strategy provided)
        groups: dict[str, list[TFinding]] | None = None
        if self._grouping_strategy:
            groups = self._grouping_strategy.group(findings)

        # Step 2: Sample (if sampling strategy provided)
        findings_to_enrich: list[TFinding] = findings
        if self._sampling_strategy:
            # Use groups if available, otherwise create implicit single group
            groups_for_sampling = groups if groups else {"_all": findings}
            sampling_result = self._sampling_strategy.sample(groups_for_sampling)
            # Flatten sampled findings from all groups
            findings_to_enrich = [
                f
                for group_samples in sampling_result.sampled.values()
                for f in group_samples
            ]

        # Step 3: Call strategy with findings
        try:
            strategy_result = self._enrichment_strategy.enrich(
                findings_to_enrich, config, run_id
            )
            return EnrichmentResult(
                strategy_result=strategy_result,
                all_findings=findings,
                groups=groups,
                skipped=[],
            )
        except Exception:
            # Strategy failed - mark all findings as skipped
            return EnrichmentResult(
                strategy_result=None,
                all_findings=findings,
                groups=groups,
                skipped=[
                    SkippedFinding(finding=f, reason=SkipReason.BATCH_ERROR)
                    for f in findings_to_enrich
                ],
            )
