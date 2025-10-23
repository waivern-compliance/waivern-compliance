"""LLM validation strategy for personal data analysis."""

import logging
from typing import Any, override

from waivern_analysers_shared.llm_validation import (
    LLMValidationStrategy,
)
from waivern_analysers_shared.types import LLMValidationConfig
from waivern_community.prompts.personal_data_validation import (
    get_batch_validation_prompt,
)
from waivern_llm import BaseLLMService

from .schemas.types import PersonalDataFindingModel

logger = logging.getLogger(__name__)


class PersonalDataValidationStrategy(LLMValidationStrategy[PersonalDataFindingModel]):
    """LLM validation strategy for personal data findings."""

    @override
    def get_validation_prompt(
        self,
        findings_batch: list[PersonalDataFindingModel],
        config: LLMValidationConfig,
    ) -> str:
        """Generate validation prompt for personal data findings."""
        findings_for_prompt = self.convert_findings_for_prompt(findings_batch)
        return get_batch_validation_prompt(findings_for_prompt)

    @override
    def convert_findings_for_prompt(
        self, findings_batch: list[PersonalDataFindingModel]
    ) -> list[dict[str, Any]]:
        """Convert PersonalDataFindingModel objects to format expected by validation prompt."""
        findings_for_prompt: list[dict[str, Any]] = []
        for finding in findings_batch:
            findings_for_prompt.append(
                {
                    "type": finding.type,
                    "risk_level": finding.risk_level,
                    "special_category": finding.special_category,
                    "matched_patterns": finding.matched_patterns,
                    "evidence": [item.content for item in finding.evidence],
                    "metadata": finding.metadata,
                }
            )
        return findings_for_prompt

    @override
    def get_finding_identifier(self, finding: PersonalDataFindingModel) -> str:
        """Get human-readable identifier for personal data finding."""
        return f"{finding.type} - {', '.join(finding.matched_patterns)}"


def personal_data_validation_strategy(
    findings: list[PersonalDataFindingModel],
    config: LLMValidationConfig,
    llm_service: BaseLLMService,
) -> tuple[list[PersonalDataFindingModel], bool]:
    """LLM validation strategy for personal data findings.

    This strategy validates personal data findings using LLM to filter false positives.
    It processes findings in batches and uses specialized prompts for personal data validation.

    Args:
        findings: List of typed PersonalDataFindingModel objects to validate
        config: Configuration including batch_size, validation_mode, etc.
        llm_service: LLM service instance

    Returns:
        Tuple of (validated findings, validation_succeeded)

    """
    strategy = PersonalDataValidationStrategy()
    return strategy.validate_findings(findings, config, llm_service)
