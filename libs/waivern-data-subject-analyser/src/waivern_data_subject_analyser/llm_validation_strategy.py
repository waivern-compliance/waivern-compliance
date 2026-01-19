"""LLM validation strategy for data subject analysis."""

from typing import override

from waivern_analysers_shared.llm_validation import (
    DefaultLLMValidationStrategy,
)
from waivern_analysers_shared.types import LLMValidationConfig

from waivern_data_subject_analyser.prompts import get_data_subject_validation_prompt
from waivern_data_subject_analyser.schemas import DataSubjectIndicatorModel


class DataSubjectValidationStrategy(
    DefaultLLMValidationStrategy[DataSubjectIndicatorModel]
):
    """LLM validation strategy for data subject indicators."""

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
