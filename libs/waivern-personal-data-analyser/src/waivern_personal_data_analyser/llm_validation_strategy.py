"""LLM validation strategy for personal data analysis."""

from typing import override

from waivern_analysers_shared.llm_validation import (
    FilteringLLMValidationStrategy,
)
from waivern_analysers_shared.types import LLMValidationConfig

from .prompts.personal_data_validation import get_personal_data_validation_prompt
from .schemas.types import PersonalDataIndicatorModel


class PersonalDataValidationStrategy(
    FilteringLLMValidationStrategy[PersonalDataIndicatorModel]
):
    """LLM validation strategy for personal data indicators.

    Uses the filtering paradigm to validate personal data indicators,
    categorising them as TRUE_POSITIVE (keep) or FALSE_POSITIVE (remove).
    """

    @override
    def get_validation_prompt(
        self,
        findings_batch: list[PersonalDataIndicatorModel],
        config: LLMValidationConfig,
    ) -> str:
        """Generate validation prompt for personal data indicators."""
        return get_personal_data_validation_prompt(
            findings_batch,
            validation_mode=config.llm_validation_mode,
        )
