"""LLM analysis runner for delegating validation logic to analysers."""

import logging
from collections.abc import Callable
from typing import Any, TypeVar

from typing_extensions import override

from wct.analysers.runners.base import AnalysisRunner
from wct.analysers.runners.types import LLMValidationConfig
from wct.analysers.utilities import LLMServiceManager
from wct.llm_service import AnthropicLLMService

logger = logging.getLogger(__name__)

# Constants
_ANALYSIS_RUNNER_TYPE_IDENTIFIER = "llm_validation_runner"

# Type variable for LLM analysis results
ResultT = TypeVar("ResultT")


class LLMAnalysisRunner(AnalysisRunner[ResultT, LLMValidationConfig]):
    """Generic LLM analysis runner that delegates validation logic to analysers.

    This runner provides the infrastructure for LLM validation including service
    management and error handling, while allowing each analyser to define specific
    validation strategies through callable functions.
    """

    def __init__(
        self,
        validation_strategy: Callable[
            [list[ResultT], LLMValidationConfig, Any], list[ResultT]
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
        self.validation_strategy = validation_strategy or self._passthrough_strategy

    @override
    def get_analysis_type(self) -> str:
        """Return the analysis type identifier."""
        return _ANALYSIS_RUNNER_TYPE_IDENTIFIER

    @override
    def run_analysis(
        self,
        input_data: list[ResultT],
        metadata: dict[str, Any],
        config: LLMValidationConfig,
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

            # Execute validation strategy directly
            llm_service = self.llm_service_manager.llm_service
            if llm_service is None:
                # This should not happen due to _should_skip_validation check,
                # but we handle it for type safety
                logger.warning("LLM service is None, returning input data unchanged")
                return input_data

            validated_findings = self.validation_strategy(
                input_data, config, llm_service
            )

            logger.info(
                f"LLM validation completed: {len(input_data)} → {len(validated_findings)} findings"
            )
            return validated_findings

        except Exception as e:
            logger.error(f"LLM validation failed: {e}")
            logger.warning("Returning unvalidated findings due to LLM validation error")
            return input_data

    def _passthrough_strategy(
        self,
        findings: list[ResultT],
        config: LLMValidationConfig,
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

    def _should_skip_validation(
        self, input_data: list[ResultT], config: LLMValidationConfig
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
