"""LLM validation strategy for data subject analysis."""

from typing import override

from waivern_analysers_shared.llm_validation.models import LLMValidationResponseModel
from waivern_analysers_shared.llm_validation.strategy import FilteringValidationStrategy
from waivern_analysers_shared.types import LLMValidationConfig
from waivern_llm import BatchingMode, ItemGroup, LLMRequest
from waivern_schemas.data_subject_indicator import DataSubjectIndicatorModel

from .prompts.prompt_builder import DataSubjectPromptBuilder


class DataSubjectValidationStrategy(
    FilteringValidationStrategy[DataSubjectIndicatorModel]
):
    """Count-based filtering strategy for data subject indicators.

    ``prepare_validation()`` builds a single COUNT_BASED LLMRequest for
    dispatch by the executor. Response deserialisation and outcome
    categorisation are inherited from ``FilteringValidationStrategy``.
    """

    @override
    def prepare_validation(
        self,
        findings: list[DataSubjectIndicatorModel],
        config: LLMValidationConfig,
        run_id: str,
    ) -> tuple[
        list[DataSubjectIndicatorModel],
        LLMRequest[DataSubjectIndicatorModel] | None,
    ]:
        """Build a COUNT_BASED LLMRequest for data subject validation."""
        if not findings:
            return ([], None)

        request: LLMRequest[DataSubjectIndicatorModel] = LLMRequest(
            groups=[ItemGroup(items=findings, content=None)],
            prompt_builder=DataSubjectPromptBuilder(
                validation_mode=config.llm_validation_mode
            ),
            response_model=LLMValidationResponseModel,
            batching_mode=BatchingMode.COUNT_BASED,
            run_id=run_id,
        )
        return (findings, request)
