"""Orchestration factory for data subject validation.

Creates ValidationOrchestrator instances configured with concern-based
grouping and random sampling. DataSubjectAnalyser groups findings by
``subject_category`` (e.g., "Customer", "Employee") so group-level
decisions can propagate to non-sampled findings.
"""

from waivern_analysers_shared.llm_validation import (
    ConcernGroupingStrategy,
    RandomSamplingStrategy,
    ValidationOrchestrator,
)
from waivern_analysers_shared.types import LLMValidationConfig
from waivern_schemas.data_subject_indicator import DataSubjectIndicatorModel

from waivern_data_subject_analyser.llm_validation_strategy import (
    DataSubjectValidationStrategy,
)

from .providers import DataSubjectConcernProvider


def create_validation_orchestrator(
    config: LLMValidationConfig,
) -> ValidationOrchestrator[DataSubjectIndicatorModel]:
    """Create orchestrator configured for data subject validation.

    Args:
        config: LLM validation configuration (provides sampling_size).

    Returns:
        Configured ValidationOrchestrator instance.

    """
    return ValidationOrchestrator(
        llm_strategy=DataSubjectValidationStrategy(),
        grouping_strategy=ConcernGroupingStrategy(DataSubjectConcernProvider()),
        sampling_strategy=RandomSamplingStrategy[DataSubjectIndicatorModel](
            config.sampling_size
        ),
    )
