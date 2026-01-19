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

        Decision logic:
        1. flag_for_review → keep (conservative, regardless of validation_result)
        2. FALSE_POSITIVE → remove
        3. TRUE_POSITIVE → keep

        Args:
            result: LLM validation result
            finding: The finding being evaluated.

        Returns:
            True if finding should be kept, False otherwise

        """
        # Keep findings flagged for review (conservative approach)
        if result.recommended_action == "flag_for_review":
            return True

        # Remove false positives
        if result.validation_result == "FALSE_POSITIVE":
            logger.info(
                f"Removed false positive: {finding} "
                f"(confidence: {result.confidence:.2f}) - {result.reasoning}"
            )
            return False

        # Keep true positives
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
