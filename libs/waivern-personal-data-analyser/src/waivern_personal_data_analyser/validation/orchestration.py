"""Orchestration factory for personal data validation.

Creates ValidationOrchestrator instances configured with concern-based
grouping and random sampling. PersonalDataAnalyser groups findings by
category (e.g., "email", "phone", "health") so group-level decisions can
propagate to non-sampled findings.
"""

from waivern_analysers_shared.llm_validation import (
    ConcernGroupingStrategy,
    RandomSamplingStrategy,
    ValidationOrchestrator,
)
from waivern_analysers_shared.types import LLMValidationConfig
from waivern_schemas.personal_data_indicator import PersonalDataIndicatorModel

from waivern_personal_data_analyser.llm_validation_strategy import (
    PersonalDataValidationStrategy,
)

from .providers import PersonalDataConcernProvider


def create_validation_orchestrator(
    config: LLMValidationConfig,
) -> ValidationOrchestrator[PersonalDataIndicatorModel]:
    """Create orchestrator configured for personal data validation.

    Args:
        config: LLM validation configuration (provides sampling_size).

    Returns:
        Configured ValidationOrchestrator instance.

    """
    return ValidationOrchestrator(
        llm_strategy=PersonalDataValidationStrategy(),
        grouping_strategy=ConcernGroupingStrategy(PersonalDataConcernProvider()),
        sampling_strategy=RandomSamplingStrategy[PersonalDataIndicatorModel](
            config.sampling_size
        ),
    )
