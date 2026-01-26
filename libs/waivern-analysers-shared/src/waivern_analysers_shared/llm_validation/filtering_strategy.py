"""Filtering LLM validation strategy for keep/remove decisions.

This strategy implements the **filtering** paradigm where the LLM determines
which findings are TRUE_POSITIVE (keep) or FALSE_POSITIVE (remove).

Flow
----

::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                   FilteringLLMValidationStrategy                        │
    ├─────────────────────────────────────────────────────────────────────────┤
    │                                                                         │
    │  Findings ──► Batch by count ──► For each batch:                        │
    │                     │                    │                              │
    │                     │                    └──► validate_batch()          │
    │                     │                         • get_validation_prompt() │
    │                     │                         • LLM call                │
    │                     │                         • Categorise findings     │
    │                     │                                                   │
    │                     └──► Aggregate ──► LLMValidationOutcome             │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘

This is the standard filtering strategy. For strategies that need full source
content, use :class:`ExtendedContextLLMValidationStrategy` instead.
"""

import logging
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import override

from waivern_core import Finding
from waivern_llm import BaseLLMService

from waivern_analysers_shared.types import LLMValidationConfig

from .decision_engine import ValidationDecisionEngine
from .default_strategy import DefaultLLMValidationStrategy
from .models import (
    SKIP_REASON_BATCH_ERROR,
    LLMValidationOutcome,
    LLMValidationResponseModel,
    LLMValidationResultModel,
    SkippedFinding,
)

logger = logging.getLogger(__name__)


@dataclass
class _FilteringBatchResult[T]:
    """Result of filtering validation for a single batch."""

    kept: list[T] = field(default_factory=list)
    removed: list[T] = field(default_factory=list)
    not_flagged: list[T] = field(default_factory=list)


class FilteringLLMValidationStrategy[TFinding: Finding](
    DefaultLLMValidationStrategy[
        TFinding,
        LLMValidationOutcome[TFinding],
        _FilteringBatchResult[TFinding],
    ]
):
    """LLM validation strategy for filtering (keep/remove findings).

    Implements the filtering paradigm where the LLM categorises findings as
    TRUE_POSITIVE (keep) or FALSE_POSITIVE (remove). Findings not mentioned
    by the LLM are kept (fail-safe behaviour).

    Subclasses must implement ``get_validation_prompt()`` to generate
    prompts for the LLM.

    Type parameter TFinding is the finding type, must satisfy the Finding protocol.
    """

    # -------------------------------------------------------------------------
    # Abstract: Prompt Generation
    # -------------------------------------------------------------------------

    @abstractmethod
    def get_validation_prompt(
        self, findings_batch: list[TFinding], config: LLMValidationConfig
    ) -> str:
        """Generate validation prompt for a batch of findings.

        Args:
            findings_batch: Batch of findings to validate.
            config: LLM validation configuration.

        Returns:
            Validation prompt string for the LLM.

        """
        ...

    # -------------------------------------------------------------------------
    # Batch Validation
    # -------------------------------------------------------------------------

    @override
    def _validate_batch(
        self,
        findings_batch: list[TFinding],
        config: LLMValidationConfig,
        llm_service: BaseLLMService,
    ) -> _FilteringBatchResult[TFinding]:
        """Validate a batch using the filtering paradigm.

        1. Generate prompt using get_validation_prompt()
        2. Call LLM with LLMValidationResponseModel
        3. Categorise findings as kept/removed/not_flagged

        Args:
            findings_batch: Batch of findings to validate.
            config: LLM validation configuration.
            llm_service: LLM service instance.

        Returns:
            BatchResult with findings categorised.

        """
        prompt = self.get_validation_prompt(findings_batch, config)

        logger.debug(f"Validating batch of {len(findings_batch)} findings")
        response = llm_service.invoke_with_structured_output(
            prompt, LLMValidationResponseModel
        )
        logger.debug(f"Received {len(response.results)} validation results")

        return self._categorise_findings_by_validation_results(
            findings_batch, response.results
        )

    # -------------------------------------------------------------------------
    # Result Aggregation
    # -------------------------------------------------------------------------

    @override
    def _aggregate_batch_results(
        self,
        batch_results: list[_FilteringBatchResult[TFinding]],
        failed_batches: list[list[TFinding]],
    ) -> LLMValidationOutcome[TFinding]:
        """Aggregate filtering results from all batches.

        Args:
            batch_results: Results from successful batches.
            failed_batches: Findings from batches that failed LLM validation.

        Returns:
            LLMValidationOutcome with aggregated results.

        """
        all_kept: list[TFinding] = []
        all_removed: list[TFinding] = []
        all_not_flagged: list[TFinding] = []
        all_skipped: list[SkippedFinding[TFinding]] = []

        # Aggregate successful batch results
        for batch_result in batch_results:
            all_kept.extend(batch_result.kept)
            all_removed.extend(batch_result.removed)
            all_not_flagged.extend(batch_result.not_flagged)

        # Failed batches become skipped findings
        for failed_batch in failed_batches:
            all_skipped.extend(
                SkippedFinding(finding=f, reason=SKIP_REASON_BATCH_ERROR)
                for f in failed_batch
            )

        outcome = LLMValidationOutcome(
            llm_validated_kept=all_kept,
            llm_validated_removed=all_removed,
            llm_not_flagged=all_not_flagged,
            skipped=all_skipped,
        )

        logger.debug(
            f"LLM validation completed: "
            f"{len(outcome.kept_findings)} kept "
            f"({len(all_kept)} validated, "
            f"{len(all_not_flagged)} not flagged, "
            f"{len(all_skipped)} skipped)"
        )

        return outcome

    @override
    def _handle_total_failure(
        self, findings: list[TFinding]
    ) -> LLMValidationOutcome[TFinding]:
        """Handle total validation failure by marking all findings as skipped.

        Args:
            findings: All findings that were to be validated.

        Returns:
            LLMValidationOutcome with all findings marked as skipped.

        """
        return LLMValidationOutcome(
            llm_validated_kept=[],
            llm_validated_removed=[],
            llm_not_flagged=[],
            skipped=[
                SkippedFinding(finding=f, reason=SKIP_REASON_BATCH_ERROR)
                for f in findings
            ],
        )

    # -------------------------------------------------------------------------
    # Filtering Logic
    # -------------------------------------------------------------------------

    def _categorise_findings_by_validation_results(
        self,
        findings_batch: list[TFinding],
        validation_results: list[LLMValidationResultModel],
    ) -> _FilteringBatchResult[TFinding]:
        """Categorise findings based on LLM validation results.

        Uses fail-safe approach: findings not mentioned by LLM are categorised
        as 'not_flagged' and kept.

        Args:
            findings_batch: Original batch of findings.
            validation_results: Strongly-typed validation results from LLM.

        Returns:
            BatchResult with findings categorised as kept, removed, or not_flagged.

        """
        # Build lookup from finding ID to finding
        findings_by_id = {f.id: f for f in findings_batch}
        result = _FilteringBatchResult[TFinding]()
        processed_ids: set[str] = set()

        for llm_result in validation_results:
            finding = findings_by_id.get(llm_result.finding_id)

            if finding is None:
                logger.warning(f"Unknown finding_id from LLM: {llm_result.finding_id}")
                continue

            processed_ids.add(llm_result.finding_id)

            # Log validation decision using optimised engine
            ValidationDecisionEngine.log_validation_decision(llm_result, finding)

            # Categorise based on decision engine
            if ValidationDecisionEngine.should_keep_finding(llm_result, finding):
                result.kept.append(finding)
            else:
                result.removed.append(finding)

        # Findings not flagged by LLM are considered valid (true positives)
        # LLM only returns false positives to save output tokens
        not_flagged_ids = set(findings_by_id.keys()) - processed_ids

        if not_flagged_ids:
            logger.debug(
                f"{len(not_flagged_ids)} findings not flagged by LLM, keeping as valid"
            )
            for finding_id in not_flagged_ids:
                result.not_flagged.append(findings_by_id[finding_id])

        return result
