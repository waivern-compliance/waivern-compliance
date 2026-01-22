"""Unified validation decision engine for LLM validation results."""

import logging

from waivern_core import Finding

from .models import LLMValidationResultModel

logger = logging.getLogger(__name__)


class ValidationDecisionEngine:
    """Validation decision engine."""

    @staticmethod
    def should_keep_finding(
        result: LLMValidationResultModel,
        finding: Finding,
    ) -> bool:
        """Determine whether a finding should be kept based on validation results.

        Decision logic:
        1. flag_for_review → keep (conservative, regardless of validation_result)
        2. FALSE_POSITIVE → remove
        3. TRUE_POSITIVE → keep

        Note: Most validation prompts instruct the LLM to only return FALSE_POSITIVE
        findings (to save output tokens). In those cases, TRUE_POSITIVE findings are
        simply omitted from the response and handled separately as "not_flagged".
        This method still handles explicit TRUE_POSITIVE results to support prompts
        that may be configured to return all validation results.

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
        finding: Finding,
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
