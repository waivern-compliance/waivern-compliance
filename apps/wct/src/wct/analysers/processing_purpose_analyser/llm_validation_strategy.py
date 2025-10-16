"""LLM validation strategy for processing purpose analysis."""

import logging
from typing import Any, override

from waivern_llm import BaseLLMService

from wct.analysers.llm_validation import (
    LLMValidationStrategy,
)
from wct.analysers.types import LLMValidationConfig
from wct.prompts.processing_purpose_validation import (
    get_processing_purpose_validation_prompt,
)

from .types import ProcessingPurposeFindingModel

logger = logging.getLogger(__name__)


class ProcessingPurposeValidationStrategy(
    LLMValidationStrategy[ProcessingPurposeFindingModel]
):
    """LLM validation strategy for processing purpose findings."""

    @override
    def get_validation_prompt(
        self,
        findings_batch: list[ProcessingPurposeFindingModel],
        config: LLMValidationConfig,
    ) -> str:
        """Generate validation prompt for processing purpose findings."""
        return get_processing_purpose_validation_prompt(
            findings_batch, config.llm_validation_mode
        )

    @override
    def convert_findings_for_prompt(
        self, findings_batch: list[ProcessingPurposeFindingModel]
    ) -> list[dict[str, Any]]:
        """Convert ProcessingPurposeFindingModel objects to format expected by validation prompt."""
        return [finding.model_dump() for finding in findings_batch]

    @override
    def get_finding_identifier(self, finding: ProcessingPurposeFindingModel) -> str:
        """Get human-readable identifier for processing purpose finding."""
        return f"{finding.purpose} - {', '.join(finding.matched_patterns)}"


def processing_purpose_validation_strategy(
    findings: list[ProcessingPurposeFindingModel],
    config: LLMValidationConfig,
    llm_service: BaseLLMService,
) -> tuple[list[ProcessingPurposeFindingModel], bool]:
    """LLM validation strategy for processing purpose findings.

    This strategy validates processing purpose findings using LLM to filter false positives.
    It processes findings in batches and uses specialized prompts for processing purpose validation.

    Args:
        findings: List of typed ProcessingPurposeFindingModel objects to validate
        config: Configuration including batch_size, validation_mode, etc.
        llm_service: LLM service instance

    Returns:
        Tuple of (validated findings, validation_succeeded)

    """
    strategy = ProcessingPurposeValidationStrategy()
    return strategy.validate_findings(findings, config, llm_service)
