"""Orchestration factory for processing purpose validation.

Creates ValidationOrchestrator instances configured for processing purpose
analysis, with LLM strategy selection based on input schema and optional
sampling based on configuration.

Architecture notes:
    This factory makes two types of decisions:

    1. **LLM Strategy Selection** (design-time, schema-dependent):
       - source_code schema + content available → ExtendedContextLLMValidationStrategy
       - Otherwise → simple finding-based strategy
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
       - ProcessingPurposeValidationStrategy: inline, follows tested pattern
       - SourceCodeValidationStrategy: tested in test_extended_context_strategy.py
       - ValidationOrchestrator: tested in waivern-analysers-shared
       - ConcernGroupingStrategy/RandomSamplingStrategy: tested in waivern-analysers-shared
    3. The complete validation flow is verified by integration tests

    If you add non-trivial logic (e.g., complex strategy selection, error
    handling, validation), you SHOULD add tests for that behaviour.
"""

from typing import override

from waivern_analysers_shared.llm_validation import (
    ConcernGroupingStrategy,
    FilteringLLMValidationStrategy,
    LLMValidationStrategy,
    RandomSamplingStrategy,
    ValidationOrchestrator,
)
from waivern_analysers_shared.types import LLMValidationConfig
from waivern_llm.v2 import LLMService

from waivern_processing_purpose_analyser.llm_validation_strategy import (
    ProcessingPurposeValidationStrategy,
)
from waivern_processing_purpose_analyser.prompts.prompt_builder import (
    ProcessingPurposePromptBuilder,
)
from waivern_processing_purpose_analyser.schemas.types import (
    ProcessingPurposeIndicatorModel,
)

from .extended_context_strategy import SourceCodeValidationStrategy
from .providers import (
    ProcessingPurposeConcernProvider,
    SourceCodeSourceProvider,
)


class _LegacyProcessingPurposeValidationStrategy(
    FilteringLLMValidationStrategy[ProcessingPurposeIndicatorModel]
):
    """Legacy finding-based validation strategy for processing purposes.

    Uses the filtering paradigm (v1) to validate processing purpose findings,
    categorising them as TRUE_POSITIVE (keep) or FALSE_POSITIVE (remove).

    This is used as fallback for source_code schema until Step 13b migrates
    extended context validation. For standard_input schema, use the v2
    ProcessingPurposeValidationStrategy instead.

    TODO: Post-migration cleanup (Step 13b):
        Remove this class after SourceCodeValidationStrategy is migrated to v2.
    """

    @override
    def get_validation_prompt(
        self,
        findings_batch: list[ProcessingPurposeIndicatorModel],
        config: LLMValidationConfig,
    ) -> str:
        """Generate validation prompt for processing purpose findings."""
        builder = ProcessingPurposePromptBuilder(
            validation_mode=config.llm_validation_mode
        )
        return builder.build_prompt(findings_batch)


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
        llm_service: LLM service instance for v2 validation (standard_input schema).

    Returns:
        Configured ValidationOrchestrator instance.

    """
    # LLM Strategy: Design-time decision based on input schema
    # - standard_input: Use v2 ProcessingPurposeValidationStrategy (if llm_service available)
    # - source_code: Use v1 SourceCodeValidationStrategy (migrated in Step 13b)
    llm_strategy: LLMValidationStrategy[ProcessingPurposeIndicatorModel, object]
    fallback_strategy: (
        FilteringLLMValidationStrategy[ProcessingPurposeIndicatorModel] | None
    ) = None

    if input_schema_name == "source_code" and source_contents:
        # Extended context strategy (v1 - migrated in Step 13b)
        source_provider = SourceCodeSourceProvider(source_contents)
        llm_strategy = SourceCodeValidationStrategy(source_provider)
        # Fallback to evidence-only strategy for findings that can't be validated
        # with extended context (e.g., oversized sources, missing content)
        # TODO: Post-migration cleanup (Step 13b):
        #   Replace with v2 ProcessingPurposeValidationStrategy as fallback
        fallback_strategy = _LegacyProcessingPurposeValidationStrategy()
    elif llm_service:
        # Standard input with v2 service available - use v2 strategy
        llm_strategy = ProcessingPurposeValidationStrategy(llm_service)
        # No fallback needed - already using evidence-only strategy
    else:
        # Fallback to v1 strategy when no llm_service provided
        llm_strategy = _LegacyProcessingPurposeValidationStrategy()

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
