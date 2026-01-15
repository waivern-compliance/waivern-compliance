"""Default LLM validation strategy with count-based batching."""

import logging
from abc import abstractmethod
from typing import override

from waivern_core.schemas import BaseFindingModel
from waivern_llm import BaseLLMService

from waivern_analysers_shared.types import LLMValidationConfig

from .decision_engine import ValidationDecisionEngine
from .models import LLMValidationResponseModel, LLMValidationResultModel
from .strategy import LLMValidationStrategy

logger = logging.getLogger(__name__)


class DefaultLLMValidationStrategy[T: BaseFindingModel](LLMValidationStrategy[T]):
    """Default LLM validation strategy using count-based batching.

    Batches findings by fixed count (llm_batch_size) and includes evidence
    snippets in prompts. This is the standard approach suitable for most
    validation scenarios.

    Subclasses must implement prompt generation methods.

    Type parameter T is the finding type, must be a BaseFindingModel subclass.
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
    ) -> tuple[list[T], bool]:
        """Validate findings using LLM with count-based batching.

        Processes findings in batches of llm_batch_size, generates prompts
        using the subclass implementation, and filters based on LLM responses.

        Args:
            findings: List of findings to validate.
            config: Configuration including batch_size, validation_mode, etc.
            llm_service: LLM service instance.

        Returns:
            Tuple of (validated findings, all_succeeded flag).

        """
        if not findings:
            logger.debug("No findings to validate")
            return findings, True

        try:
            # Process findings in batches using shared logic
            validated_findings, all_batches_succeeded = (
                self._process_findings_in_batches(findings, config, llm_service)
            )

            logger.debug(
                f"LLM validation completed: {len(findings)} → {len(validated_findings)} findings"
            )

            return validated_findings, all_batches_succeeded

        except Exception as e:
            logger.error(f"LLM validation strategy failed: {e}")
            logger.warning(
                "Returning original findings due to validation strategy error"
            )
            return findings, False

    def _process_findings_in_batches(
        self,
        findings: list[T],
        config: LLMValidationConfig,
        llm_service: BaseLLMService,
    ) -> tuple[list[T], bool]:
        """Process findings in batches for LLM validation.

        Args:
            findings: List of finding objects to validate.
            config: LLM validation configuration.
            llm_service: LLM service instance.

        Returns:
            Tuple of (validated findings, all_batches_succeeded).

        """
        batch_size = config.llm_batch_size
        validated_findings: list[T] = []
        all_batches_succeeded = True

        for i in range(0, len(findings), batch_size):
            batch = findings[i : i + batch_size]
            try:
                batch_results = self._validate_findings_batch(
                    batch, config, llm_service
                )
                validated_findings.extend(batch_results)
            except Exception as e:
                logger.error(
                    f"LLM validation failed for batch {i // batch_size + 1}: {e}"
                )
                logger.warning(
                    "Adding unvalidated batch to results due to validation error"
                )
                # Use resilient error handling - continue with remaining batches
                validated_findings.extend(batch)
                all_batches_succeeded = False

        return validated_findings, all_batches_succeeded

    def _validate_findings_batch(
        self,
        findings_batch: list[T],
        config: LLMValidationConfig,
        llm_service: BaseLLMService,
    ) -> list[T]:
        """Validate a batch of findings using LLM.

        Args:
            findings_batch: Batch of findings to validate.
            config: LLM validation configuration.
            llm_service: LLM service instance.

        Returns:
            List of validated findings from this batch.

        """
        # Generate validation prompt using subclass implementation
        prompt = self.get_validation_prompt(findings_batch, config)

        # Get LLM validation response with structured output
        logger.debug(f"Validating batch of {len(findings_batch)} findings")
        response = llm_service.invoke_with_structured_output(
            prompt, LLMValidationResponseModel
        )
        logger.debug(f"Received {len(response.results)} validation results")

        # Filter findings based on validation results
        return self._filter_findings_by_validation_results(
            findings_batch, response.results
        )

    def _filter_findings_by_validation_results(
        self,
        findings_batch: list[T],
        validation_results: list[LLMValidationResultModel],
    ) -> list[T]:
        """Filter findings based on LLM validation results.

        Uses fail-safe approach: findings not mentioned by LLM are included
        (with warning), consistent with existing validation error handling.

        Args:
            findings_batch: Original batch of findings.
            validation_results: Strongly-typed validation results from LLM.

        Returns:
            List of validated findings that should be kept.

        """
        # Build lookup from finding ID to finding
        findings_by_id = {f.id: f for f in findings_batch}
        validated_findings: list[T] = []
        processed_ids: set[str] = set()

        for result in validation_results:
            finding = findings_by_id.get(result.finding_id)

            if finding is None:
                logger.warning(f"Unknown finding_id from LLM: {result.finding_id}")
                continue

            processed_ids.add(result.finding_id)

            # Log validation decision using optimized engine
            ValidationDecisionEngine.log_validation_decision(result, finding)

            # Determine if finding should be kept using optimised decision engine
            if ValidationDecisionEngine.should_keep_finding(result, finding):
                validated_findings.append(finding)

        # Findings not flagged by LLM are considered valid (true positives)
        # LLM only returns false positives to save output tokens
        not_flagged_ids = set(findings_by_id.keys()) - processed_ids

        if not_flagged_ids:
            logger.debug(
                f"{len(not_flagged_ids)} findings not flagged by LLM, keeping as valid"
            )
            for finding_id in not_flagged_ids:
                validated_findings.append(findings_by_id[finding_id])

        return validated_findings
