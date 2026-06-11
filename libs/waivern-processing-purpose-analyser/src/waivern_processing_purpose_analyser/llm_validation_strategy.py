"""LLM validation strategy for processing purpose analysis."""

from typing import override

from waivern_analysers_shared.llm_validation.strategy import FilteringValidationStrategy
from waivern_analysers_shared.types import LLMValidationConfig
from waivern_core import LLMValidationResponseModel
from waivern_llm import BatchingMode, ItemGroup, LLMRequest
from waivern_schemas.processing_purpose_indicator import ProcessingPurposeIndicatorModel

from .prompts.prompt_builder import ProcessingPurposePromptBuilder


class ProcessingPurposeValidationStrategy(
    FilteringValidationStrategy[ProcessingPurposeIndicatorModel]
):
    """Count-based filtering strategy for processing purpose indicators.

    ``prepare_validation()`` builds a single COUNT_BASED LLMRequest for
    dispatch by the executor. Response deserialisation and outcome
    categorisation are inherited from ``FilteringValidationStrategy``.
    """

    @override
    def prepare_validation(
        self,
        findings: list[ProcessingPurposeIndicatorModel],
        config: LLMValidationConfig,
        run_id: str,
    ) -> tuple[
        list[ProcessingPurposeIndicatorModel],
        LLMRequest[ProcessingPurposeIndicatorModel] | None,
    ]:
        """Build a COUNT_BASED LLMRequest for processing purpose validation."""
        if not findings:
            return ([], None)

        request: LLMRequest[ProcessingPurposeIndicatorModel] = LLMRequest(
            groups=[ItemGroup(items=findings, content=None)],
            prompt_builder=ProcessingPurposePromptBuilder(
                validation_mode=config.llm_validation_mode
            ),
            response_model=LLMValidationResponseModel,
            batching_mode=BatchingMode.COUNT_BASED,
            run_id=run_id,
        )
        return (findings, request)
