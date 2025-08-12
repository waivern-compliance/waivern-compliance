"""LLM validation analysis runner."""

import logging
from collections.abc import Callable
from typing import Any

from wct.analysers.runners.base import AnalysisRunner
from wct.analysers.utilities import LLMServiceManager

logger = logging.getLogger(__name__)

# Type alias for validation strategy function
ValidationStrategyFn = Callable[
    [list[dict[str, Any]], dict[str, Any], Any], list[dict[str, Any]]
]


class LLMValidationRunner(AnalysisRunner[dict[str, Any]]):
    """Generic LLM validation runner that delegates specific validation logic to analysers.

    This runner provides the infrastructure for LLM validation (service management,
    batching, error handling) but allows each analyser to define how findings
    are validated and processed.
    """

    def __init__(
        self,
        validation_strategy: ValidationStrategyFn | None = None,
        enable_llm_validation: bool = True,
    ):
        """Initialise the LLM validation runner.

        Args:
            validation_strategy: Function that defines how to validate findings.
                               If None, findings are returned unchanged.
            enable_llm_validation: Whether LLM validation is enabled

        """
        self.llm_service_manager = LLMServiceManager(enable_llm_validation)
        self.validation_strategy = (
            validation_strategy
            if validation_strategy is not None
            else self._passthrough_strategy
        )

    def get_analysis_type(self) -> str:
        """Return the analysis type identifier."""
        return "llm_validation"

    def run_analysis(
        self,
        input_data: list[dict[str, Any]],
        metadata: dict[str, Any],
        config: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Run LLM validation on findings.

        Args:
            input_data: List of findings to validate
            metadata: Metadata about the analysis context
            config: Configuration including:
                - enable_llm_validation: Whether to enable validation (default: True)
                - llm_batch_size: Batch size for processing (default: 10)
                - other analyser-specific config

        Returns:
            List of validated findings (filtered/modified by validation strategy)

        Raises:
            AnalysisRunnerError: If LLM validation fails

        """
        try:
            if not config.get("enable_llm_validation", True) or not input_data:
                logger.debug("LLM validation disabled or no findings to validate")
                return input_data

            if not self.llm_service_manager.is_available():
                logger.warning("LLM service not available, skipping validation")
                return input_data

            logger.info(f"Starting LLM validation of {len(input_data)} findings")

            # Delegate to the analyser-specific validation strategy
            validated_findings = self.validation_strategy(
                input_data, config, self.llm_service_manager.llm_service
            )

            logger.info(
                f"LLM validation completed: {len(input_data)} → {len(validated_findings)} findings"
            )

            return validated_findings

        except Exception as e:
            # Log the error but don't fail the entire analysis
            logger.error(f"LLM validation failed: {e}")
            logger.warning("Returning unvalidated findings due to LLM validation error")
            return input_data

    def _passthrough_strategy(
        self, findings: list[dict[str, Any]], config: dict[str, Any], llm_service: Any
    ) -> list[dict[str, Any]]:
        """Return findings unchanged as a default passthrough strategy.

        Args:
            findings: List of findings to validate
            config: Configuration parameters
            llm_service: LLM service instance

        Returns:
            Original findings list unchanged

        """
        logger.debug("Using passthrough validation strategy (no filtering)")
        return findings

    def create_batch_validation_strategy(
        self,
        prompt_generator: Callable[[list[dict[str, Any]]], str],
        response_parser: Callable[[str, list[dict[str, Any]]], list[dict[str, Any]]],
    ) -> ValidationStrategyFn:
        """Create a batch validation strategy with custom prompt and response handling.

        This is a helper method to create validation strategies that follow the
        common pattern of: batch findings -> generate prompt -> call LLM -> parse response.

        Args:
            prompt_generator: Function to generate LLM prompt from findings batch
            response_parser: Function to parse LLM response and return validated findings

        Returns:
            A validation strategy function that can be used with this runner

        """

        def batch_validation_strategy(
            findings: list[dict[str, Any]], config: dict[str, Any], llm_service: Any
        ) -> list[dict[str, Any]]:
            """Batch validation strategy implementation."""
            batch_size = config.get("llm_batch_size", 10)
            validated_findings = []

            # Process findings in batches
            for i in range(0, len(findings), batch_size):
                batch = findings[i : i + batch_size]

                try:
                    # Generate prompt for this batch
                    prompt = prompt_generator(batch)

                    # Get LLM response
                    logger.debug(f"Validating batch of {len(batch)} findings")
                    response = llm_service.analyse_data("", prompt)

                    # Parse response and get validated findings
                    batch_results = response_parser(response, batch)
                    validated_findings.extend(batch_results)

                except Exception as e:
                    logger.error(f"Batch validation failed: {e}")
                    # On batch failure, include original findings for safety
                    logger.warning("Including unvalidated batch due to error")
                    validated_findings.extend(batch)

            return validated_findings

        return batch_validation_strategy
