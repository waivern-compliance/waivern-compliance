"""Risk modifier validation strategy using LLM.

This strategy implements the **enrichment** paradigm where the LLM detects
risk modifiers (e.g., minor, vulnerable_individual) for data subject findings.
Results are aggregated at the category level.

Flow
----

::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                   RiskModifierValidationStrategy                        │
    ├─────────────────────────────────────────────────────────────────────────┤
    │                                                                         │
    │  Findings ──► Create ItemGroup ──► LLMService.complete()                │
    │                                           │                             │
    │                                           └──► Parse responses          │
    │                                                      │                  │
    │                                                      └──► Aggregate     │
    │                                                           by category   │
    │                                                              │          │
    │                                              RiskModifierValidationResult│
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘

Unlike filtering strategies (keep/remove), this strategy **enriches** findings
with risk modifiers at the category level.

Implements the EnrichmentStrategy protocol from waivern-analysers-shared.
"""

import asyncio
import logging
from collections import defaultdict

from waivern_llm import (
    BatchingMode,
    ItemGroup,
    LLMService,
    SkippedFinding,
)
from waivern_rulesets import RiskModifier

from waivern_gdpr_data_subject_classifier.prompts import RiskModifierPromptBuilder
from waivern_gdpr_data_subject_classifier.schemas import GDPRDataSubjectFindingModel

from .models import (
    CategoryRiskModifierResult,
    RiskModifierValidationResponseModel,
    RiskModifierValidationResult,
)

logger = logging.getLogger(__name__)


class RiskModifierValidationStrategy:
    """LLM validation strategy for detecting risk modifiers.

    Implements the EnrichmentStrategy protocol where the LLM identifies
    risk modifiers (e.g., minor, vulnerable_individual) for data subject
    findings. Results are aggregated at the category level using union
    semantics.

    The strategy receives LLMService via constructor injection and calls
    `enrich()` to detect risk modifiers.
    """

    def __init__(
        self,
        available_modifiers: list[RiskModifier],
        llm_service: LLMService,
    ) -> None:
        """Initialise strategy with available modifiers and LLM service.

        Args:
            available_modifiers: List of risk modifiers from the ruleset
                that the LLM should look for.
            llm_service: LLMService instance for making validation calls.

        """
        self._available_modifiers = available_modifiers
        self._llm_service = llm_service
        self._prompt_builder = RiskModifierPromptBuilder(available_modifiers)

    def enrich(
        self,
        findings: list[GDPRDataSubjectFindingModel],
        run_id: str,
    ) -> RiskModifierValidationResult:
        """Enrich findings with risk modifiers using LLM.

        Orchestrates the enrichment flow:
        1. Wrap findings in ItemGroup for LLMService
        2. Call LLMService.complete() with prompt builder
        3. Parse responses and aggregate by category
        4. Handle skipped findings gracefully

        Args:
            findings: Findings to enrich.
            run_id: Run ID for cache scoping.

        Returns:
            RiskModifierValidationResult with category-level modifiers.

        """
        if not findings:
            return RiskModifierValidationResult(
                category_results=[],
                total_findings=0,
                total_sampled=0,
                validation_succeeded=True,
            )

        try:
            return asyncio.run(self._enrich_async(findings, run_id))
        except Exception as e:
            logger.error(f"LLM enrichment failed: {e}")
            return self._handle_total_failure(findings)

    async def _enrich_async(
        self,
        findings: list[GDPRDataSubjectFindingModel],
        run_id: str,
    ) -> RiskModifierValidationResult:
        """Async enrichment implementation."""
        # Wrap findings in a single ItemGroup (no content needed for COUNT_BASED)
        groups = [ItemGroup(items=findings, content=None)]

        result = await self._llm_service.complete(
            groups,
            prompt_builder=self._prompt_builder,
            response_model=RiskModifierValidationResponseModel,
            batching_mode=BatchingMode.COUNT_BASED,
            run_id=run_id,
        )

        return self._aggregate_results(findings, result.responses, result.skipped)

    def _aggregate_results(
        self,
        findings: list[GDPRDataSubjectFindingModel],
        responses: list[RiskModifierValidationResponseModel],
        skipped: list[SkippedFinding[GDPRDataSubjectFindingModel]],
    ) -> RiskModifierValidationResult:
        """Aggregate LLM responses into category-level results.

        Groups findings by category and aggregates:
        - Modifiers: union of all modifiers in category
        - Confidence: average of all finding confidences
        - Count: number of findings per category

        Args:
            findings: All findings that were sent for enrichment.
            responses: Responses from successful LLM calls.
            skipped: Findings that could not be processed.

        Returns:
            Aggregated result with category-level risk modifiers.

        """
        # Build lookup from finding ID to finding
        findings_by_id = {f.id: f for f in findings}

        # Accumulators for category-level aggregation
        category_modifiers: dict[str, set[str]] = defaultdict(set)
        category_confidences: dict[str, list[float]] = defaultdict(list)
        category_counts: dict[str, int] = defaultdict(int)

        # Process all responses
        for response in responses:
            for result in response.results:
                finding = findings_by_id.get(result.finding_id)
                if finding is None:
                    logger.warning(f"Unknown finding_id from LLM: {result.finding_id}")
                    continue

                category = finding.data_subject_category
                category_modifiers[category].update(result.risk_modifiers)
                category_confidences[category].append(result.confidence)
                category_counts[category] += 1

        # Build category results
        category_results = [
            CategoryRiskModifierResult(
                category=cat,
                detected_modifiers=sorted(category_modifiers[cat]),
                sample_count=category_counts[cat],
                confidence=(
                    sum(category_confidences[cat]) / len(category_confidences[cat])
                    if category_confidences[cat]
                    else 0.0
                ),
            )
            for cat in category_modifiers
        ]

        total_sampled = sum(category_counts.values())
        has_skipped = len(skipped) > 0

        return RiskModifierValidationResult(
            category_results=category_results,
            total_findings=len(findings),
            total_sampled=total_sampled,
            validation_succeeded=not has_skipped,
        )

    def _handle_total_failure(
        self,
        findings: list[GDPRDataSubjectFindingModel],
    ) -> RiskModifierValidationResult:
        """Handle total validation failure.

        Called when an unexpected exception occurs at the strategy level.
        Returns a fail-safe result with no modifiers detected.

        Args:
            findings: All findings that were to be enriched.

        Returns:
            Empty result with validation_succeeded=False.

        """
        return RiskModifierValidationResult(
            category_results=[],
            total_findings=len(findings),
            total_sampled=0,
            validation_succeeded=False,
        )
