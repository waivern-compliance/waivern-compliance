"""LLM analysis runner."""

import logging
from collections.abc import Callable
from typing import Any, TypeVar

from typing_extensions import override

from wct.analysers.runners.base import AnalysisRunner
from wct.analysers.runners.types import LLMAnalysisRunnerConfig
from wct.analysers.utilities import LLMServiceManager
from wct.llm_service import AnthropicLLMService

logger = logging.getLogger(__name__)

# Constants
_ANALYSIS_RUNNER_TYPE_IDENTIFIER = "llm_validation"
_EMPTY_PROMPT_DATA = ""

# Type variable for LLM analysis results
ResultT = TypeVar("ResultT")


class LLMAnalysisRunner(AnalysisRunner[ResultT, LLMAnalysisRunnerConfig]):
    """Generic LLM analysis runner that delegates specific validation logic to analysers.

    This runner provides the infrastructure for LLM validation (service management,
    batching, error handling) but allows each analyser to define how findings
    are validated and processed.
    """

    def __init__(
        self,
        validation_strategy: Callable[
            [list[ResultT], LLMAnalysisRunnerConfig, Any], list[ResultT]
        ]
        | None = None,
        enable_llm_validation: bool = True,
    ) -> None:
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

    @override
    def get_analysis_type(self) -> str:
        """Return the analysis type identifier."""
        return _ANALYSIS_RUNNER_TYPE_IDENTIFIER

    @override
    def run_analysis(
        self,
        input_data: list[ResultT],
        metadata: dict[str, Any],
        config: LLMAnalysisRunnerConfig,
    ) -> list[ResultT]:
        """Run LLM validation on findings.

        Args:
            input_data: List of findings to validate
            metadata: Metadata about the analysis context
            config: Configuration for LLM analysis and validation

        Returns:
            List of validated findings (filtered/modified by validation strategy)

        Raises:
            AnalysisRunnerError: If LLM validation fails

        """
        try:
            if self._should_skip_validation(input_data, config):
                return input_data

            logger.info(f"Starting LLM validation of {len(input_data)} findings")

            validated_findings = self._execute_validation_strategy(input_data, config)

            self._log_validation_results(len(input_data), len(validated_findings))
            return validated_findings

        except Exception as e:
            return self._handle_validation_error(e, input_data)

    def _passthrough_strategy(
        self,
        findings: list[ResultT],
        config: LLMAnalysisRunnerConfig,
        llm_service: AnthropicLLMService,
    ) -> list[ResultT]:
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
        prompt_generator: Callable[[list[ResultT]], str],
        response_parser: Callable[[str, list[ResultT]], list[ResultT]],
    ) -> Callable[[list[ResultT], LLMAnalysisRunnerConfig, Any], list[ResultT]]:
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
            findings: list[ResultT],
            config: LLMAnalysisRunnerConfig,
            llm_service: AnthropicLLMService,
        ) -> list[ResultT]:
            """Batch validation strategy implementation."""
            batch_size = config.llm_batch_size
            validated_findings: list[ResultT] = []

            # Process findings in batches
            for i in range(0, len(findings), batch_size):
                batch = findings[i : i + batch_size]
                batch_results = self._process_validation_batch(
                    batch, prompt_generator, response_parser, llm_service
                )
                validated_findings.extend(batch_results)

            return validated_findings

        return batch_validation_strategy

    def _should_skip_validation(
        self, input_data: list[ResultT], config: LLMAnalysisRunnerConfig
    ) -> bool:
        """Determine if LLM validation should be skipped.

        Args:
            input_data: List of findings to validate
            config: Configuration for LLM analysis

        Returns:
            True if validation should be skipped, False otherwise

        """
        if not config.enable_llm_validation or not input_data:
            logger.debug("LLM validation disabled or no findings to validate")
            return True

        if not self.llm_service_manager.is_available():
            logger.warning("LLM service not available, skipping validation")
            return True

        return False

    def _execute_validation_strategy(
        self, input_data: list[ResultT], config: LLMAnalysisRunnerConfig
    ) -> list[ResultT]:
        """Execute the validation strategy on input data.

        Args:
            input_data: List of findings to validate
            config: Configuration for LLM analysis

        Returns:
            List of validated findings

        """
        llm_service = self.llm_service_manager.llm_service
        if llm_service is None:
            # This should not happen due to _should_skip_validation check,
            # but we handle it for type safety
            logger.warning("LLM service is None, returning input data unchanged")
            return input_data

        return self.validation_strategy(input_data, config, llm_service)

    def _log_validation_results(
        self, original_count: int, validated_count: int
    ) -> None:
        """Log the results of validation.

        Args:
            original_count: Number of original findings
            validated_count: Number of validated findings

        """
        logger.info(
            f"LLM validation completed: {original_count} → {validated_count} findings"
        )

    def _handle_validation_error(
        self, error: Exception, input_data: list[ResultT]
    ) -> list[ResultT]:
        """Handle validation errors with appropriate logging and fallback.

        Args:
            error: The exception that occurred during validation
            input_data: Original input data to return as fallback

        Returns:
            Original input data unchanged

        """
        logger.error(f"LLM validation failed: {error}")
        logger.warning("Returning unvalidated findings due to LLM validation error")
        return input_data

    def _process_validation_batch(
        self,
        batch: list[ResultT],
        prompt_generator: Callable[[list[ResultT]], str],
        response_parser: Callable[[str, list[ResultT]], list[ResultT]],
        llm_service: AnthropicLLMService,
    ) -> list[ResultT]:
        """Process a single batch of findings through LLM validation.

        Args:
            batch: Batch of findings to validate
            prompt_generator: Function to generate LLM prompt from batch
            response_parser: Function to parse LLM response
            llm_service: LLM service instance

        Returns:
            List of validated findings, or original batch on error

        """
        try:
            prompt = prompt_generator(batch)
            logger.debug(f"Validating batch of {len(batch)} findings")

            response = llm_service.analyse_data(_EMPTY_PROMPT_DATA, prompt)
            return response_parser(response, batch)

        except Exception as e:
            logger.error(f"Batch validation failed: {e}")
            logger.warning("Including unvalidated batch due to error")
            return batch
