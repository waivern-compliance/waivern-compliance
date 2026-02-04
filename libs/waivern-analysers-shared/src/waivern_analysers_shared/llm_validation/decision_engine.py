"""Unified validation decision engine for LLM validation results.

Centralises all decision logic for LLM validation:
- Individual finding decisions (keep/remove based on LLM result)
- Group-level decisions (remove group, keep partial, keep all)
"""

import logging
from typing import Literal

from waivern_core import Finding

from .models import LLMValidationResultModel

logger = logging.getLogger(__name__)


# Type alias for group decision outcomes
GroupDecision = Literal["remove_group", "keep_partial", "keep_all"]


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

    # -------------------------------------------------------------------------
    # Group-Level Decisions
    # -------------------------------------------------------------------------

    @staticmethod
    def classify_group(kept_count: int, removed_count: int) -> GroupDecision:
        """Classify a group based on validation results of its samples.

        Decision logic:
        - No validated samples → keep_all (conservative, nothing to base decision on)
        - All validated samples FALSE_POSITIVE → remove_group (Case A)
        - Mixed results → keep_partial (Case B/C: keep group, remove only FPs)

        Args:
            kept_count: Number of samples marked TRUE_POSITIVE or not flagged.
            removed_count: Number of samples marked FALSE_POSITIVE.

        Returns:
            GroupDecision indicating what action to take on the group.

        """
        total_validated = kept_count + removed_count

        if total_validated == 0:
            return "keep_all"

        if removed_count == total_validated:
            return "remove_group"

        return "keep_partial"
