"""Unified validation decision engine for LLM validation results."""

import logging

from waivern_core.schemas import BaseFindingModel

from .models import LLMValidationResultModel

logger = logging.getLogger(__name__)


class ValidationDecisionEngine:
    """Validation decision engine."""

    @staticmethod
    def should_keep_finding(
        result: LLMValidationResultModel,
        finding: BaseFindingModel,
    ) -> bool:
        """Determine whether a finding should be kept based on validation results.

        Unified logic supporting both analysers with FLAG_FOR_REVIEW handling.
        Optimized decision tree for performance.

        Args:
            result: LLM validation result
            finding: The finding being evaluated.

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
            logger.info(
                f"Removed false positive: {finding} "
                f"(confidence: {result.confidence:.2f}) - {result.reasoning}"
            )
            return False

        # Conservative fallback: Keep uncertain findings for safety
        logger.warning(
            f"Uncertain validation result for {finding}, keeping for safety: {result.reasoning}"
        )
        return True

    @staticmethod
    def log_validation_decision(
        result: LLMValidationResultModel,
        finding: BaseFindingModel,
    ) -> None:
        """Log validation decision with consistent format.

        Args:
            result: LLM validation result
            finding: The finding being evaluated.

        """
        logger.debug(
            f"Finding '{finding}': "
            f"{result.validation_result} (confidence: {result.confidence:.2f}) - {result.reasoning}"
        )
