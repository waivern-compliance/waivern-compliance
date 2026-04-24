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
       - ConcernGroupingStrategy/ValidationOrchestrator: tested in waivern-analysers-shared
    3. The complete validation flow is verified by integration tests

    If you add non-trivial logic (e.g., complex strategy selection, error
    handling, validation), you SHOULD add tests for that behaviour.
"""

from waivern_analysers_shared.llm_validation import (
    ConcernGroupingStrategy,
    LLMValidationStrategy,
    ValidationOrchestrator,
)
from waivern_analysers_shared.types import LLMValidationConfig
from waivern_core.types import JsonValue
from waivern_schemas.processing_purpose_indicator import (
    ProcessingPurposeIndicatorModel,
)

from waivern_processing_purpose_analyser.llm_validation_strategy import (
    ProcessingPurposeValidationStrategy,
)

from .extended_context_strategy import (
    SourceCodeStrategyState,
    SourceCodeValidationStrategy,
)
from .providers import (
    ProcessingPurposeConcernProvider,
    SourceCodeSourceProvider,
)


def create_validation_orchestrator(
    config: LLMValidationConfig,
    input_schema_name: str,
    source_contents: dict[str, str] | None = None,
    strategy_state: dict[str, JsonValue] | None = None,
) -> ValidationOrchestrator[ProcessingPurposeIndicatorModel]:
    """Create orchestrator configured for processing purpose validation.

    Args:
        config: LLM validation configuration.
        input_schema_name: Name of the input schema (e.g., "source_code", "standard_input").
        source_contents: Map of file paths to content. Round-1 callers pass this
            directly from the input messages.
        strategy_state: Persisted ``SourceCodeValidationStrategy`` state used to
            reconstruct the orchestrator on fallback/resume rounds. Consulted
            only when ``source_contents`` is not provided. Opaque to callers;
            its shape is defined by the strategy's ``export_persistence_state()``.

    Returns:
        Configured ValidationOrchestrator instance.

    """
    # LLM Strategy: Design-time decision based on input schema
    # - source_code: SourceCodeValidationStrategy (EXTENDED_CONTEXT batching)
    # - standard_input: ProcessingPurposeValidationStrategy (COUNT_BASED batching)
    llm_strategy: LLMValidationStrategy[ProcessingPurposeIndicatorModel, object]
    fallback_strategy: (
        LLMValidationStrategy[ProcessingPurposeIndicatorModel, object] | None
    ) = None

    if input_schema_name == "source_code":
        # Reconstruction: recover source_contents from persisted strategy state
        # when the caller did not supply them directly (round-2 / resume path).
        if source_contents is None and strategy_state is not None:
            source_contents = SourceCodeStrategyState.model_validate(
                strategy_state
            ).source_contents

        # Extended context strategy - uses full file content for validation.
        # An empty provider (missing contents) routes all findings to the
        # fallback via SkipReason.MISSING_CONTENT — graceful degradation.
        source_provider = SourceCodeSourceProvider(source_contents or {})
        llm_strategy = SourceCodeValidationStrategy(source_provider)
        # Fallback to evidence-only strategy for findings that can't be validated
        # with extended context (e.g., oversized sources, missing content)
        fallback_strategy = ProcessingPurposeValidationStrategy()
    else:
        # Standard input - use evidence-only strategy
        llm_strategy = ProcessingPurposeValidationStrategy()
        # No fallback needed - already using evidence-only strategy

    # Grouping: Design-time decision
    # ProcessingPurposeAnalyser groups findings by purpose (e.g., "Payment Processing",
    # "User Authentication"). This enables group-level decision logic - if all findings
    # for a purpose are false positives, the entire purpose can be removed.
    concern_provider = ProcessingPurposeConcernProvider()
    grouping_strategy = ConcernGroupingStrategy(concern_provider)

    return ValidationOrchestrator(
        llm_strategy=llm_strategy,
        grouping_strategy=grouping_strategy,
        sample_size=config.sampling_size,
        fallback_strategy=fallback_strategy,
    )
