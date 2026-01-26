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
    │  Findings ──► Batch by count ──► For each batch:                        │
    │                     │                    │                              │
    │                     │                    └──► _validate_batch()         │
    │                     │                         • Generate prompt         │
    │                     │                         • Call LLM                │
    │                     │                         • Parse response          │
    │                     │                                                   │
    │                     └──► _aggregate_batch_results()                     │
    │                              • Group by category                        │
    │                              • Union modifiers                          │
    │                              • Average confidence                       │
    │                                        │                                │
    │                                        └──► RiskModifierValidationResult│
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘

Unlike FilteringLLMValidationStrategy (keep/remove), this strategy **enriches**
findings with risk modifiers at the category level.
"""

import logging
from collections import defaultdict
from typing import override

from waivern_analysers_shared.llm_validation import DefaultLLMValidationStrategy
from waivern_analysers_shared.types import LLMValidationConfig
from waivern_llm import BaseLLMService
from waivern_rulesets import RiskModifier

from waivern_gdpr_data_subject_classifier.prompts.risk_modifier_validation import (
    get_risk_modifier_validation_prompt,
)
from waivern_gdpr_data_subject_classifier.schemas import GDPRDataSubjectFindingModel

from .models import (
    CategoryRiskModifierResult,
    RiskModifierBatchResult,
    RiskModifierValidationResponseModel,
    RiskModifierValidationResult,
)

logger = logging.getLogger(__name__)


class RiskModifierValidationStrategy(
    DefaultLLMValidationStrategy[
        GDPRDataSubjectFindingModel,
        RiskModifierValidationResult,
        RiskModifierBatchResult,
    ]
):
    """LLM validation strategy for detecting risk modifiers.

    Implements the enrichment paradigm where the LLM identifies risk modifiers
    (e.g., minor, vulnerable_individual) for data subject findings. Results
    are aggregated at the category level using union semantics.

    Args:
        available_modifiers: List of risk modifiers from the ruleset.

    """

    def __init__(self, available_modifiers: list[RiskModifier]) -> None:
        """Initialise strategy with available modifiers.

        Args:
            available_modifiers: List of risk modifiers from the ruleset
                that the LLM should look for.

        """
        self._available_modifiers = available_modifiers

    # -------------------------------------------------------------------------
    # Batch Validation
    # -------------------------------------------------------------------------

    @override
    def _validate_batch(
        self,
        findings_batch: list[GDPRDataSubjectFindingModel],
        config: LLMValidationConfig,
        llm_service: BaseLLMService,
    ) -> RiskModifierBatchResult:
        """Validate a batch of findings for risk modifiers.

        1. Generate prompt using the risk modifier validation prompt
        2. Call LLM with RiskModifierValidationResponseModel
        3. Parse response into batch result

        Args:
            findings_batch: Batch of findings to validate.
            config: LLM validation configuration.
            llm_service: LLM service instance.

        Returns:
            Batch result with modifiers, confidences, and categories per finding.

        """
        prompt = get_risk_modifier_validation_prompt(
            findings_batch, self._available_modifiers
        )

        logger.debug(
            f"Validating batch of {len(findings_batch)} findings for risk modifiers"
        )
        response = llm_service.invoke_with_structured_output(
            prompt, RiskModifierValidationResponseModel
        )
        logger.debug(f"Received {len(response.results)} risk modifier results")

        return self._parse_batch_response(findings_batch, response)

    def _parse_batch_response(
        self,
        findings_batch: list[GDPRDataSubjectFindingModel],
        response: RiskModifierValidationResponseModel,
    ) -> RiskModifierBatchResult:
        """Parse LLM response into batch result."""
        # Build lookup from finding ID to finding
        id_to_finding = {f.id: f for f in findings_batch}

        finding_modifiers: dict[str, list[str]] = {}
        finding_confidences: dict[str, float] = {}
        finding_categories: dict[str, str] = {}

        # Record categories for all findings in batch
        for finding in findings_batch:
            finding_categories[finding.id] = finding.data_subject_category

        # Extract modifiers from LLM response
        for result in response.results:
            if result.finding_id not in id_to_finding:
                logger.warning(f"Unknown finding_id from LLM: {result.finding_id}")
                continue

            finding_modifiers[result.finding_id] = result.risk_modifiers
            finding_confidences[result.finding_id] = result.confidence

        return RiskModifierBatchResult(
            finding_modifiers=finding_modifiers,
            finding_confidences=finding_confidences,
            finding_categories=finding_categories,
        )

    # -------------------------------------------------------------------------
    # Result Aggregation
    # -------------------------------------------------------------------------

    @override
    def _aggregate_batch_results(
        self,
        batch_results: list[RiskModifierBatchResult],
        failed_batches: list[list[GDPRDataSubjectFindingModel]],
    ) -> RiskModifierValidationResult:
        """Aggregate batch results into category-level results.

        Groups findings by category and aggregates:
        - Modifiers: union of all modifiers in category
        - Confidence: average of all finding confidences
        - Count: number of findings per category

        Args:
            batch_results: Results from successful batches.
            failed_batches: Findings from batches that failed LLM validation.

        Returns:
            Aggregated result with category-level risk modifiers.

        """
        # Accumulators for category-level aggregation
        category_modifiers: dict[str, set[str]] = defaultdict(set)
        category_confidences: dict[str, list[float]] = defaultdict(list)
        category_counts: dict[str, int] = defaultdict(int)

        # Aggregate from successful batches
        for batch in batch_results:
            for finding_id, modifiers in batch.finding_modifiers.items():
                category = batch.finding_categories[finding_id]
                category_modifiers[category].update(modifiers)
                category_counts[category] += 1

                if finding_id in batch.finding_confidences:
                    category_confidences[category].append(
                        batch.finding_confidences[finding_id]
                    )

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
        total_failed = sum(len(batch) for batch in failed_batches)

        return RiskModifierValidationResult(
            category_results=category_results,
            total_findings=total_sampled + total_failed,
            total_sampled=total_sampled,
            validation_succeeded=len(failed_batches) == 0,
        )

    # -------------------------------------------------------------------------
    # Failure Handling
    # -------------------------------------------------------------------------

    @override
    def _handle_total_failure(
        self, findings: list[GDPRDataSubjectFindingModel]
    ) -> RiskModifierValidationResult:
        """Handle total validation failure.

        Called when an unexpected exception occurs at the strategy level.
        Returns a fail-safe result with no modifiers detected.

        Args:
            findings: All findings that were to be validated.

        Returns:
            Empty result with validation_succeeded=False.

        """
        return RiskModifierValidationResult(
            category_results=[],
            total_findings=len(findings),
            total_sampled=0,
            validation_succeeded=False,
        )
