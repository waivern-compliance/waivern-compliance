"""LLM validation strategy for personal data analysis."""

from typing import Any, override

from waivern_analysers_shared.llm_validation import (
    DefaultLLMValidationStrategy,
)
from waivern_analysers_shared.types import LLMValidationConfig

from .prompts.personal_data_validation import get_batch_validation_prompt
from .schemas.types import PersonalDataIndicatorModel


class PersonalDataValidationStrategy(
    DefaultLLMValidationStrategy[PersonalDataIndicatorModel]
):
    """LLM validation strategy for personal data indicators."""

    @override
    def get_validation_prompt(
        self,
        findings_batch: list[PersonalDataIndicatorModel],
        config: LLMValidationConfig,
    ) -> str:
        """Generate validation prompt for personal data indicators."""
        findings_for_prompt = self._convert_findings_for_prompt(findings_batch)
        return get_batch_validation_prompt(findings_for_prompt)

    def _convert_findings_for_prompt(
        self, findings_batch: list[PersonalDataIndicatorModel]
    ) -> list[dict[str, Any]]:
        """Convert findings to dictionary format for the validation prompt."""
        findings_for_prompt: list[dict[str, Any]] = []
        for finding in findings_batch:
            findings_for_prompt.append(
                {
                    "id": finding.id,
                    "category": finding.category,
                    "matched_patterns": finding.matched_patterns,
                    "evidence": [item.content for item in finding.evidence],
                    "metadata": finding.metadata,
                }
            )
        return findings_for_prompt
