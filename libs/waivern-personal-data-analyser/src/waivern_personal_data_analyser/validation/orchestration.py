"""Orchestration factory for personal data validation.

Creates ValidationOrchestrator instances configured for personal data
analysis, with grouping and sampling based on configuration.
"""

from waivern_analysers_shared.llm_validation import (
    ConcernGroupingStrategy,
    GroupingStrategy,
    RandomSamplingStrategy,
    SamplingStrategy,
    ValidationOrchestrator,
)
from waivern_analysers_shared.types import LLMValidationConfig

from waivern_personal_data_analyser.llm_validation_strategy import (
    PersonalDataValidationStrategy,
)
from waivern_personal_data_analyser.schemas.types import PersonalDataIndicatorModel

from .providers import PersonalDataConcernProvider


def create_validation_orchestrator(
    config: LLMValidationConfig,
) -> ValidationOrchestrator[PersonalDataIndicatorModel]:
    """Create orchestrator configured for personal data validation.

    PersonalDataAnalyser only supports standard_input schema, so it uses
    the simple finding-based strategy (no extended context).

    Grouping and sampling are enabled when sampling_size is configured.

    Args:
        config: LLM validation configuration.

    Returns:
        Configured ValidationOrchestrator instance.

    """
    # PersonalDataAnalyser uses simple finding-based validation
    llm_strategy = PersonalDataValidationStrategy()

    # Add grouping/sampling when sampling_size is configured
    grouping_strategy: GroupingStrategy[PersonalDataIndicatorModel] | None = None
    sampling_strategy: SamplingStrategy[PersonalDataIndicatorModel] | None = None
    if config.sampling_size is not None:
        concern_provider = PersonalDataConcernProvider()
        grouping_strategy = ConcernGroupingStrategy(concern_provider)
        sampling_strategy = RandomSamplingStrategy(config.sampling_size)

    return ValidationOrchestrator(
        llm_strategy=llm_strategy,
        grouping_strategy=grouping_strategy,
        sampling_strategy=sampling_strategy,
    )
