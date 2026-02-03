"""Orchestration factory for personal data validation.

Creates ValidationOrchestrator instances configured for personal data
analysis, with grouping and optional sampling based on configuration.

Architecture notes:
    Grouping vs Sampling are separate concerns:

    - **Grouping** is a design-time decision made by the analyser. Each analyser
      knows whether its findings should be grouped and by what attribute (via
      ConcernProvider). PersonalDataAnalyser groups by `category`.

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
       - PersonalDataValidationStrategy: tested in test_llm_validation_strategy.py
       - ValidationOrchestrator: tested in waivern-analysers-shared
       - ConcernGroupingStrategy/RandomSamplingStrategy: tested in waivern-analysers-shared
    3. The complete validation flow is verified by integration tests

    If you add non-trivial logic (e.g., strategy selection based on schema,
    error handling, validation), you SHOULD add tests for that behaviour.
"""

from waivern_analysers_shared.llm_validation import (
    ConcernGroupingStrategy,
    RandomSamplingStrategy,
    ValidationOrchestrator,
)
from waivern_analysers_shared.types import LLMValidationConfig
from waivern_llm.v2 import LLMService

from waivern_personal_data_analyser.llm_validation_strategy import (
    PersonalDataValidationStrategy,
)
from waivern_personal_data_analyser.schemas.types import PersonalDataIndicatorModel

from .providers import PersonalDataConcernProvider


def create_validation_orchestrator(
    config: LLMValidationConfig,
    llm_service: LLMService,
) -> ValidationOrchestrator[PersonalDataIndicatorModel]:
    """Create orchestrator configured for personal data validation.

    PersonalDataAnalyser only supports standard_input schema, so it uses
    the simple finding-based strategy (no extended context).

    Args:
        config: LLM validation configuration.
        llm_service: LLM service instance for validation calls.

    Returns:
        Configured ValidationOrchestrator instance.

    """
    llm_strategy = PersonalDataValidationStrategy(llm_service)

    # Grouping: Design-time decision
    # PersonalDataAnalyser groups findings by category (e.g., "email", "phone",
    # "health"). This enables group-level decision logic - if all findings in
    # a category are false positives, the entire category can be removed.
    concern_provider = PersonalDataConcernProvider()
    grouping_strategy = ConcernGroupingStrategy(concern_provider)

    # Sampling: Runtime configuration (always enabled, defaults to 3)
    # Only a sample of findings per group is validated by the LLM. This reduces
    # cost for large datasets while still applying group-level decisions to all.
    sampling_strategy: RandomSamplingStrategy[PersonalDataIndicatorModel] = (
        RandomSamplingStrategy(config.sampling_size)
    )

    return ValidationOrchestrator(
        llm_strategy=llm_strategy,
        grouping_strategy=grouping_strategy,
        sampling_strategy=sampling_strategy,
    )
