"""LLM validation strategy for data subject analysis."""

from typing import override

from waivern_analysers_shared.llm_validation import (
    FilteringLLMValidationStrategy,
)
from waivern_analysers_shared.types import LLMValidationConfig

from waivern_data_subject_analyser.prompts import get_data_subject_validation_prompt
from waivern_data_subject_analyser.schemas import DataSubjectIndicatorModel


class DataSubjectValidationStrategy(
    FilteringLLMValidationStrategy[DataSubjectIndicatorModel]
):
    """LLM validation strategy for data subject indicators.

    Uses the filtering paradigm to validate data subject indicators,
    categorising them as TRUE_POSITIVE (keep) or FALSE_POSITIVE (remove).
    """

    @override
    def get_validation_prompt(
        self,
        findings_batch: list[DataSubjectIndicatorModel],
        config: LLMValidationConfig,
    ) -> str:
        """Generate validation prompt for data subject indicators."""
        return get_data_subject_validation_prompt(
            findings_batch,
            validation_mode=config.llm_validation_mode,
        )
