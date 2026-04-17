"""LLM validation strategy for personal data analysis."""

from typing import override

from waivern_analysers_shared.llm_validation.models import LLMValidationResponseModel
from waivern_analysers_shared.llm_validation.strategy import FilteringValidationStrategy
from waivern_analysers_shared.types import LLMValidationConfig
from waivern_llm import BatchingMode, ItemGroup, LLMRequest
from waivern_schemas.personal_data_indicator import PersonalDataIndicatorModel

from .prompts.prompt_builder import PersonalDataPromptBuilder


class PersonalDataValidationStrategy(
    FilteringValidationStrategy[PersonalDataIndicatorModel]
):
    """Count-based filtering strategy for personal data indicators.

    ``prepare_validation()`` builds a single COUNT_BASED LLMRequest for
    dispatch by the executor. Response deserialisation and outcome
    categorisation are inherited from ``FilteringValidationStrategy``.
    """

    @override
    def prepare_validation(
        self,
        findings: list[PersonalDataIndicatorModel],
        config: LLMValidationConfig,
        run_id: str,
    ) -> tuple[
        list[PersonalDataIndicatorModel],
        LLMRequest[PersonalDataIndicatorModel] | None,
    ]:
        """Build a COUNT_BASED LLMRequest for personal data validation."""
        if not findings:
            return ([], None)

        request: LLMRequest[PersonalDataIndicatorModel] = LLMRequest(
            groups=[ItemGroup(items=findings, content=None)],
            prompt_builder=PersonalDataPromptBuilder(
                validation_mode=config.llm_validation_mode
            ),
            response_model=LLMValidationResponseModel,
            batching_mode=BatchingMode.COUNT_BASED,
            run_id=run_id,
        )
        return (findings, request)
