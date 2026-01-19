"""Orchestration factory for data subject validation.

Creates ValidationOrchestrator instances configured for data subject
analysis, with grouping and optional sampling based on configuration.

Architecture notes:
    Grouping vs Sampling are separate concerns:

    - **Grouping** is a design-time decision made by the analyser. Each analyser
      knows whether its findings should be grouped and by what attribute (via
      ConcernProvider). DataSubjectAnalyser groups by `subject_category`.

    - **Sampling** is a runtime configuration for cost/performance tradeoffs.
      When enabled, only a sample of findings per group is validated by the LLM,
      and group-level decisions propagate to non-sampled findings.

    The ValidationOrchestrator supports grouping without sampling - when no
    sampling strategy is provided, all findings are validated but group-level
    decision logic (Case A/B/C) still applies.

Testing rationale:
    This factory function has NO dedicated unit tests because:

    1. It contains only simple wiring logic (no runtime behaviour to test)
    2. The components it assembles are tested independently:
       - DataSubjectValidationStrategy: tested in test_llm_validation_strategy.py
       - ValidationOrchestrator: tested in waivern-analysers-shared
       - ConcernGroupingStrategy/RandomSamplingStrategy: tested in waivern-analysers-shared
    3. The complete validation flow is verified by integration tests (Step 7)
    4. This pattern is consistent with PersonalDataAnalyser and
       ProcessingPurposeAnalyser, which also have no orchestration factory tests

    If you add non-trivial logic (e.g., strategy selection based on schema,
    error handling, validation), you SHOULD add tests for that behaviour.
"""

from waivern_analysers_shared.llm_validation import (
    ConcernGroupingStrategy,
    RandomSamplingStrategy,
    SamplingStrategy,
    ValidationOrchestrator,
)
from waivern_analysers_shared.types import LLMValidationConfig

from waivern_data_subject_analyser.llm_validation_strategy import (
    DataSubjectValidationStrategy,
)
from waivern_data_subject_analyser.schemas import DataSubjectIndicatorModel

from .providers import DataSubjectConcernProvider


def create_validation_orchestrator(
    config: LLMValidationConfig,
) -> ValidationOrchestrator[DataSubjectIndicatorModel]:
    """Create orchestrator configured for data subject validation.

    DataSubjectAnalyser uses the simple finding-based strategy (no extended
    context) as the evidence snippets in findings provide sufficient context
    for validation.

    Args:
        config: LLM validation configuration.

    Returns:
        Configured ValidationOrchestrator instance.

    """
    llm_strategy = DataSubjectValidationStrategy()

    # Grouping: Design-time decision
    # DataSubjectAnalyser groups findings by subject_category (e.g., "Customer",
    # "Employee"). This enables group-level decision logic - if all findings in
    # a category are false positives, the entire category can be removed.
    concern_provider = DataSubjectConcernProvider()
    grouping_strategy = ConcernGroupingStrategy(concern_provider)

    # Sampling: Runtime configuration
    # When sampling_size is configured, only a sample of findings per group is
    # validated by the LLM. This reduces cost for large datasets while still
    # applying group-level decisions to all findings.
    sampling_strategy: SamplingStrategy[DataSubjectIndicatorModel] | None = None
    if config.sampling_size is not None:
        sampling_strategy = RandomSamplingStrategy(config.sampling_size)

    return ValidationOrchestrator(
        llm_strategy=llm_strategy,
        grouping_strategy=grouping_strategy,
        sampling_strategy=sampling_strategy,
    )
