"""Unified validation decision engine for LLM validation results."""

import logging
from collections.abc import Callable
from typing import TypeVar

from .models import LLMValidationResultModel

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ValidationDecisionEngine:
    """Validation decision engine."""

    @staticmethod
    def should_keep_finding(
        result: LLMValidationResultModel,
        finding: T,
        get_identifier_func: Callable[[T], str],
    ) -> bool:
        """Determine whether a finding should be kept based on validation results.

        Unified logic supporting both analysers with FLAG_FOR_REVIEW handling.
        Optimized decision tree for performance.

        Args:
            result: LLM validation result
            finding: The finding being evaluated
            get_identifier_func: Function to get human-readable identifier

        Returns:
            True if finding should be kept, False otherwise

        """
        # Fast path: Keep validated true positives
        if (
            result.validation_result == "TRUE_POSITIVE"
            and result.recommended_action == "keep"
        ):
            return True

        # Fast path: Keep findings flagged for review (conservative approach)
        if result.recommended_action == "flag_for_review":
            return True

        # Fast path: Remove clear false positives
        if result.validation_result == "FALSE_POSITIVE":
            finding_identifier = get_identifier_func(finding)
            logger.info(
                f"Removed false positive: {finding_identifier} "
                f"(confidence: {result.confidence:.2f}) - {result.reasoning}"
            )
            return False

        # Conservative fallback: Keep uncertain findings for safety
        finding_identifier = get_identifier_func(finding)
        logger.warning(
            f"Uncertain validation result for {finding_identifier}, keeping for safety: {result.reasoning}"
        )
        return True

    @staticmethod
    def log_validation_decision(
        result: LLMValidationResultModel,
        finding: T,
        get_identifier_func: Callable[[T], str],
    ) -> None:
        """Log validation decision with consistent format.

        Args:
            result: LLM validation result
            finding: The finding being evaluated
            get_identifier_func: Function to get human-readable identifier

        """
        finding_identifier = get_identifier_func(finding)
        logger.debug(
            f"Finding '{finding_identifier}': "
            f"{result.validation_result} (confidence: {result.confidence:.2f}) - {result.reasoning}"
        )
