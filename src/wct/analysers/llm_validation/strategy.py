"""Abstract base strategy for LLM validation with shared logic."""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from wct.analysers.types import LLMValidationConfig
from wct.llm_service import BaseLLMService

from .decision_engine import ValidationDecisionEngine
from .json_utils import extract_json_from_llm_response
from .models import (
    LLMValidationResultModel,
)

logger = logging.getLogger(__name__)


class LLMValidationStrategy[T](ABC):
    """Abstract base class for LLM validation strategies.

    This eliminates code duplication between Personal Data and Processing Purpose
    analysers by providing shared batch processing and validation logic.
    """

    @abstractmethod
    def get_validation_prompt(
        self, findings_batch: list[T], config: LLMValidationConfig
    ) -> str:
        """Generate validation prompt for a batch of findings.

        Args:
            findings_batch: Batch of findings to validate
            config: LLM validation configuration

        Returns:
            Validation prompt string for the LLM

        """
        pass

    @abstractmethod
    def convert_findings_for_prompt(
        self, findings_batch: list[T]
    ) -> list[dict[str, Any]]:
        """Convert typed finding objects to format expected by validation prompt.

        Args:
            findings_batch: Batch of findings to convert

        Returns:
            List of finding dictionaries formatted for prompt

        """
        pass

    def validate_findings(
        self,
        findings: list[T],
        config: LLMValidationConfig,
        llm_service: BaseLLMService,
    ) -> tuple[list[T], bool]:
        """Validate findings using LLM with shared batch processing logic.

        Args:
            findings: List of typed finding objects to validate
            config: Configuration including batch_size, validation_mode, etc.
            llm_service: LLM service instance

        Returns:
            Tuple of (validated findings, validation_succeeded)

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

        Shared logic extracted from both Personal Data and Processing Purpose analysers.

        Args:
            findings: List of finding objects to validate
            config: LLM validation configuration
            llm_service: LLM service instance

        Returns:
            Tuple of (validated findings, all_batches_succeeded)

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
            findings_batch: Batch of findings to validate
            config: LLM validation configuration
            llm_service: LLM service instance

        Returns:
            List of validated findings from this batch

        """
        # Generate validation prompt using subclass implementation
        prompt = self.get_validation_prompt(findings_batch, config)

        # Get LLM validation response
        logger.debug(f"Validating batch of {len(findings_batch)} findings")
        response = llm_service.analyse_data("", prompt)

        try:
            # Extract and parse JSON response using unified implementation
            clean_json = extract_json_from_llm_response(response)
            validation_results = json.loads(clean_json)

            # Filter findings based on validation results
            return self._filter_findings_by_validation_results(
                findings_batch, validation_results
            )
        except (ValueError, json.JSONDecodeError) as e:
            # JSON parsing errors should bubble up to indicate validation failure
            logger.error(f"JSON parsing failed: {e}")
            raise

    def _filter_findings_by_validation_results(
        self,
        findings_batch: list[T],
        validation_results: list[dict[str, Any]],
    ) -> list[T]:
        """Filter findings based on LLM validation results.

        Shared logic extracted from both analysers.

        Args:
            findings_batch: Original batch of findings
            validation_results: Validation results from LLM

        Returns:
            List of validated findings that should be kept

        """
        validated_findings: list[T] = []

        for i, result_data in enumerate(validation_results):
            if i >= len(findings_batch):
                logger.warning(
                    f"Validation result index {i} exceeds batch size {len(findings_batch)}"
                )
                continue

            # Use strongly typed model for validation results
            try:
                result = LLMValidationResultModel.model_validate(result_data)
            except Exception as e:
                logger.warning(f"Failed to parse validation result {i}: {e}")
                # Use defaults for malformed results
                result = LLMValidationResultModel()

            finding = findings_batch[i]

            # Log validation decision using optimized engine
            ValidationDecisionEngine.log_validation_decision(
                result, finding, self.get_finding_identifier
            )

            # Determine if finding should be kept using optimized decision engine
            if ValidationDecisionEngine.should_keep_finding(
                result, finding, self.get_finding_identifier
            ):
                validated_findings.append(finding)

        return validated_findings

    @abstractmethod
    def get_finding_identifier(self, finding: T) -> str:
        """Get a human-readable identifier for the finding for logging.

        Args:
            finding: The finding object

        Returns:
            Human-readable identifier string

        """
        pass
