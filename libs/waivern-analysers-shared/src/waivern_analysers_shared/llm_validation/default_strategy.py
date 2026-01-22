"""Default LLM validation strategy with count-based batching."""

import logging
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import override

from waivern_core import Finding
from waivern_llm import BaseLLMService

from waivern_analysers_shared.types import LLMValidationConfig

from .decision_engine import ValidationDecisionEngine
from .models import (
    SKIP_REASON_BATCH_ERROR,
    LLMValidationOutcome,
    LLMValidationResponseModel,
    LLMValidationResultModel,
    SkippedFinding,
)
from .strategy import LLMValidationStrategy

logger = logging.getLogger(__name__)


@dataclass
class _BatchResult[T]:
    """Result of validating a single batch."""

    kept: list[T] = field(default_factory=list)
    removed: list[T] = field(default_factory=list)
    not_flagged: list[T] = field(default_factory=list)


class DefaultLLMValidationStrategy[T: Finding](LLMValidationStrategy[T]):
    """Default LLM validation strategy using count-based batching.

    Batches findings by fixed count (llm_batch_size) and includes evidence
    snippets in prompts. This is the standard approach suitable for most
    validation scenarios.

    Subclasses must implement prompt generation methods.

    Type parameter T is the finding type, must satisfy the Finding protocol.
    """

    @abstractmethod
    def get_validation_prompt(
        self, findings_batch: list[T], config: LLMValidationConfig
    ) -> str:
        """Generate validation prompt for a batch of findings.

        Args:
            findings_batch: Batch of findings to validate.
            config: LLM validation configuration.

        Returns:
            Validation prompt string for the LLM.

        """
        ...

    @override
    def validate_findings(
        self,
        findings: list[T],
        config: LLMValidationConfig,
        llm_service: BaseLLMService,
    ) -> LLMValidationOutcome[T]:
        """Validate findings using LLM with count-based batching.

        Processes findings in batches of llm_batch_size, generates prompts
        using the subclass implementation, and filters based on LLM responses.

        Args:
            findings: List of findings to validate.
            config: Configuration including batch_size, validation_mode, etc.
            llm_service: LLM service instance.

        Returns:
            LLMValidationOutcome with detailed breakdown of validation results.

        """
        if not findings:
            logger.debug("No findings to validate")
            return LLMValidationOutcome(
                llm_validated_kept=[],
                llm_validated_removed=[],
                llm_not_flagged=[],
                skipped=[],
            )

        try:
            outcome = self._process_findings_in_batches(findings, config, llm_service)

            logger.debug(
                f"LLM validation completed: {len(findings)} → "
                f"{len(outcome.kept_findings)} kept "
                f"({len(outcome.llm_validated_kept)} validated, "
                f"{len(outcome.llm_not_flagged)} not flagged, "
                f"{len(outcome.skipped)} skipped)"
            )

            return outcome

        except Exception as e:
            logger.error(f"LLM validation strategy failed: {e}")
            logger.warning(
                "Returning original findings as skipped due to validation strategy error"
            )
            return LLMValidationOutcome(
                llm_validated_kept=[],
                llm_validated_removed=[],
                llm_not_flagged=[],
                skipped=[
                    SkippedFinding(finding=f, reason=SKIP_REASON_BATCH_ERROR)
                    for f in findings
                ],
            )

    def _process_findings_in_batches(
        self,
        findings: list[T],
        config: LLMValidationConfig,
        llm_service: BaseLLMService,
    ) -> LLMValidationOutcome[T]:
        """Process findings in batches for LLM validation.

        Args:
            findings: List of finding objects to validate.
            config: LLM validation configuration.
            llm_service: LLM service instance.

        Returns:
            LLMValidationOutcome with aggregated results from all batches.

        """
        batch_size = config.llm_batch_size

        # Accumulators for all batches
        all_kept: list[T] = []
        all_removed: list[T] = []
        all_not_flagged: list[T] = []
        all_skipped: list[SkippedFinding[T]] = []

        for i in range(0, len(findings), batch_size):
            batch = findings[i : i + batch_size]
            try:
                batch_result = self._validate_findings_batch(batch, config, llm_service)
                all_kept.extend(batch_result.kept)
                all_removed.extend(batch_result.removed)
                all_not_flagged.extend(batch_result.not_flagged)
            except Exception as e:
                logger.error(
                    f"LLM validation failed for batch {i // batch_size + 1}: {e}"
                )
                logger.warning(
                    "Marking batch findings as skipped due to validation error"
                )
                # Batch error - all findings in this batch are skipped
                all_skipped.extend(
                    SkippedFinding(finding=f, reason=SKIP_REASON_BATCH_ERROR)
                    for f in batch
                )

        return LLMValidationOutcome(
            llm_validated_kept=all_kept,
            llm_validated_removed=all_removed,
            llm_not_flagged=all_not_flagged,
            skipped=all_skipped,
        )

    def _validate_findings_batch(
        self,
        findings_batch: list[T],
        config: LLMValidationConfig,
        llm_service: BaseLLMService,
    ) -> _BatchResult[T]:
        """Validate a batch of findings using LLM.

        Args:
            findings_batch: Batch of findings to validate.
            config: LLM validation configuration.
            llm_service: LLM service instance.

        Returns:
            BatchResult with categorised findings from this batch.

        """
        # Generate validation prompt using subclass implementation
        prompt = self.get_validation_prompt(findings_batch, config)

        # Get LLM validation response with structured output
        logger.debug(f"Validating batch of {len(findings_batch)} findings")
        response = llm_service.invoke_with_structured_output(
            prompt, LLMValidationResponseModel
        )
        logger.debug(f"Received {len(response.results)} validation results")

        # Categorise findings based on validation results
        return self._categorise_findings_by_validation_results(
            findings_batch, response.results
        )

    def _categorise_findings_by_validation_results(
        self,
        findings_batch: list[T],
        validation_results: list[LLMValidationResultModel],
    ) -> _BatchResult[T]:
        """Categorise findings based on LLM validation results.

        Uses fail-safe approach: findings not mentioned by LLM are categorised
        as 'not_flagged' and kept, consistent with existing validation error handling.

        Args:
            findings_batch: Original batch of findings.
            validation_results: Strongly-typed validation results from LLM.

        Returns:
            BatchResult with findings categorised as kept, removed, or not_flagged.

        """
        # Build lookup from finding ID to finding
        findings_by_id = {f.id: f for f in findings_batch}
        result = _BatchResult[T]()
        processed_ids: set[str] = set()

        for llm_result in validation_results:
            finding = findings_by_id.get(llm_result.finding_id)

            if finding is None:
                logger.warning(f"Unknown finding_id from LLM: {llm_result.finding_id}")
                continue

            processed_ids.add(llm_result.finding_id)

            # Log validation decision using optimized engine
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
