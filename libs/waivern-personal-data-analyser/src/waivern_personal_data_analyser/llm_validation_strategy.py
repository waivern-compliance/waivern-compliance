"""LLM validation strategy for personal data analysis."""

import logging
from typing import Any, override

from waivern_analysers_shared.llm_validation import (
    LLMValidationStrategy,
)
from waivern_analysers_shared.types import LLMValidationConfig
from waivern_llm import BaseLLMService

from .prompts.personal_data_validation import get_batch_validation_prompt
from .schemas.types import PersonalDataIndicatorModel

logger = logging.getLogger(__name__)


class PersonalDataValidationStrategy(LLMValidationStrategy[PersonalDataIndicatorModel]):
    """LLM validation strategy for personal data indicators."""

    @override
    def get_validation_prompt(
        self,
        findings_batch: list[PersonalDataIndicatorModel],
        config: LLMValidationConfig,
    ) -> str:
        """Generate validation prompt for personal data indicators."""
        findings_for_prompt = self.convert_findings_for_prompt(findings_batch)
        return get_batch_validation_prompt(findings_for_prompt)

    @override
    def convert_findings_for_prompt(
        self, findings_batch: list[PersonalDataIndicatorModel]
    ) -> list[dict[str, Any]]:
        """Convert PersonalDataIndicatorModel objects to format expected by validation prompt."""
        findings_for_prompt: list[dict[str, Any]] = []
        for finding in findings_batch:
            findings_for_prompt.append(
                {
                    "category": finding.category,
                    "matched_patterns": finding.matched_patterns,
                    "evidence": [item.content for item in finding.evidence],
                    "metadata": finding.metadata,
                }
            )
        return findings_for_prompt


def personal_data_validation_strategy(
    findings: list[PersonalDataIndicatorModel],
    config: LLMValidationConfig,
    llm_service: BaseLLMService,
) -> tuple[list[PersonalDataIndicatorModel], bool]:
    """LLM validation strategy for personal data indicators.

    This strategy validates personal data indicators using LLM to filter false positives.
    It processes indicators in batches and uses specialized prompts for personal data validation.

    Args:
        findings: List of typed PersonalDataIndicatorModel objects to validate
        config: Configuration including batch_size, validation_mode, etc.
        llm_service: LLM service instance

    Returns:
        Tuple of (validated indicators, validation_succeeded)

    """
    strategy = PersonalDataValidationStrategy()
    return strategy.validate_findings(findings, config, llm_service)
