"""Orchestration factory for processing purpose validation.

Creates ValidationOrchestrator instances configured for processing purpose
analysis, with LLM strategy selection based on input schema and optional
sampling based on configuration.

Architecture notes:
    This factory makes two types of decisions:

    1. **LLM Strategy Selection** (design-time, schema-dependent):
       - source_code schema + content available → SourceCodeValidationStrategy (EXTENDED_CONTEXT)
       - Otherwise → ProcessingPurposeValidationStrategy (COUNT_BASED, evidence-only)
       This is determined by the input schema, not runtime configuration.

    2. **Grouping vs Sampling** (separate concerns):
       - **Grouping** is a design-time decision. ProcessingPurposeAnalyser groups
         findings by `purpose`. This enables group-level decision logic - if all
         findings for a purpose are false positives, the entire purpose is removed.
       - **Sampling** is a runtime configuration for cost/performance tradeoffs.
         When enabled, only a sample of findings per group is validated by the LLM.

    The ValidationOrchestrator supports grouping without sampling - when no
    sampling strategy is provided, all findings are validated but group-level
    decision logic (Case A/B/C) still applies.

Testing rationale:
    This factory function has NO dedicated unit tests because:

    1. It contains only simple wiring logic (no runtime behaviour to test)
    2. The components it assembles are tested independently:
       - ProcessingPurposeValidationStrategy: tested in test_llm_validation_strategy.py
       - SourceCodeValidationStrategy: tested in test_llm_validation_strategy.py
       - ValidationOrchestrator: tested in waivern-analysers-shared
       - ConcernGroupingStrategy/RandomSamplingStrategy: tested in waivern-analysers-shared
    3. The complete validation flow is verified by integration tests

    If you add non-trivial logic (e.g., complex strategy selection, error
    handling, validation), you SHOULD add tests for that behaviour.
"""

from waivern_analysers_shared.llm_validation import (
    ConcernGroupingStrategy,
    LLMValidationStrategy,
    RandomSamplingStrategy,
    ValidationOrchestrator,
)
from waivern_analysers_shared.types import LLMValidationConfig
from waivern_llm.v2 import LLMService

from waivern_processing_purpose_analyser.llm_validation_strategy import (
    ProcessingPurposeValidationStrategy,
)
from waivern_processing_purpose_analyser.schemas.types import (
    ProcessingPurposeIndicatorModel,
)

from .extended_context_strategy import SourceCodeValidationStrategy
from .providers import (
    ProcessingPurposeConcernProvider,
    SourceCodeSourceProvider,
)


def create_validation_orchestrator(
    config: LLMValidationConfig,
    input_schema_name: str,
    source_contents: dict[str, str] | None = None,
    llm_service: LLMService | None = None,
) -> ValidationOrchestrator[ProcessingPurposeIndicatorModel]:
    """Create orchestrator configured for processing purpose validation.

    Args:
        config: LLM validation configuration.
        input_schema_name: Name of the input schema (e.g., "source_code", "standard_input").
        source_contents: Map of file paths to content (for source_code schema).
        llm_service: LLM service instance for validation.

    Returns:
        Configured ValidationOrchestrator instance.

    Raises:
        ValueError: If llm_service is not provided.

    """
    if llm_service is None:
        raise ValueError("llm_service is required for validation")

    # LLM Strategy: Design-time decision based on input schema
    # - source_code: SourceCodeValidationStrategy (EXTENDED_CONTEXT batching)
    # - standard_input: ProcessingPurposeValidationStrategy (COUNT_BASED batching)
    llm_strategy: LLMValidationStrategy[ProcessingPurposeIndicatorModel, object]
    fallback_strategy: (
        LLMValidationStrategy[ProcessingPurposeIndicatorModel, object] | None
    ) = None

    if input_schema_name == "source_code" and source_contents:
        # Extended context strategy - uses full file content for validation
        source_provider = SourceCodeSourceProvider(source_contents)
        llm_strategy = SourceCodeValidationStrategy(llm_service, source_provider)
        # Fallback to evidence-only strategy for findings that can't be validated
        # with extended context (e.g., oversized sources, missing content)
        fallback_strategy = ProcessingPurposeValidationStrategy(llm_service)
    else:
        # Standard input - use evidence-only strategy
        llm_strategy = ProcessingPurposeValidationStrategy(llm_service)
        # No fallback needed - already using evidence-only strategy

    # Grouping: Design-time decision
    # ProcessingPurposeAnalyser groups findings by purpose (e.g., "Payment Processing",
    # "User Authentication"). This enables group-level decision logic - if all findings
    # for a purpose are false positives, the entire purpose can be removed.
    concern_provider = ProcessingPurposeConcernProvider()
    grouping_strategy = ConcernGroupingStrategy(concern_provider)

    # Sampling: Runtime configuration (always enabled, defaults to 3)
    # Only a sample of findings per group is validated by the LLM. This reduces
    # cost for large datasets while still applying group-level decisions to all.
    sampling_strategy: RandomSamplingStrategy[ProcessingPurposeIndicatorModel] = (
        RandomSamplingStrategy(config.sampling_size)
    )

    return ValidationOrchestrator(
        llm_strategy=llm_strategy,
        grouping_strategy=grouping_strategy,
        sampling_strategy=sampling_strategy,
        fallback_strategy=fallback_strategy,
    )
