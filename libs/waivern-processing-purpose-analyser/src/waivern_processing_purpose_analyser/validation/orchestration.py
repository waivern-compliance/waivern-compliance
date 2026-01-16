"""Orchestration factory for processing purpose validation.

Creates ValidationOrchestrator instances configured for processing purpose
analysis, with LLM strategy selection based on input schema.
"""

from typing import override

from waivern_analysers_shared.llm_validation import (
    ConcernGroupingStrategy,
    DefaultLLMValidationStrategy,
    GroupingStrategy,
    RandomSamplingStrategy,
    SamplingStrategy,
    ValidationOrchestrator,
)
from waivern_analysers_shared.types import LLMValidationConfig

from waivern_processing_purpose_analyser.prompts.processing_purpose_validation import (
    get_processing_purpose_validation_prompt,
)
from waivern_processing_purpose_analyser.schemas.types import (
    ProcessingPurposeFindingModel,
)

from .extended_context_strategy import SourceCodeValidationStrategy
from .providers import (
    ProcessingPurposeConcernProvider,
    SourceCodeSourceProvider,
)


class ProcessingPurposeValidationStrategy(
    DefaultLLMValidationStrategy[ProcessingPurposeFindingModel]
):
    """Simple finding-based validation strategy for processing purposes.

    Used when source file content is not available (e.g., standard_input schema).
    """

    @override
    def get_validation_prompt(
        self,
        findings_batch: list[ProcessingPurposeFindingModel],
        config: LLMValidationConfig,
    ) -> str:
        """Generate validation prompt for processing purpose findings."""
        return get_processing_purpose_validation_prompt(
            findings_batch, config.llm_validation_mode
        )


def create_validation_orchestrator(
    config: LLMValidationConfig,
    input_schema_name: str,
    source_contents: dict[str, str] | None = None,
) -> ValidationOrchestrator[ProcessingPurposeFindingModel]:
    """Create orchestrator configured for processing purpose validation.

    LLM strategy selection is based on input schema (not configuration):
    - source_code schema + content available → ExtendedContextLLMValidationStrategy
    - Otherwise → simple finding-based strategy

    Args:
        config: LLM validation configuration.
        input_schema_name: Name of the input schema (e.g., "source_code", "standard_input").
        source_contents: Map of file paths to content (for source_code schema).

    Returns:
        Configured ValidationOrchestrator instance.

    """
    # Select LLM strategy based on input schema (internal decision, not config)
    if input_schema_name == "source_code" and source_contents:
        source_provider = SourceCodeSourceProvider(source_contents)
        llm_strategy = SourceCodeValidationStrategy(source_provider)
    else:
        llm_strategy = ProcessingPurposeValidationStrategy()

    # Add grouping/sampling when sampling_size is configured
    grouping_strategy: GroupingStrategy[ProcessingPurposeFindingModel] | None = None
    sampling_strategy: SamplingStrategy[ProcessingPurposeFindingModel] | None = None
    if config.sampling_size is not None:
        concern_provider = ProcessingPurposeConcernProvider()
        grouping_strategy = ConcernGroupingStrategy(concern_provider)
        sampling_strategy = RandomSamplingStrategy(config.sampling_size)

    return ValidationOrchestrator(
        llm_strategy=llm_strategy,
        grouping_strategy=grouping_strategy,
        sampling_strategy=sampling_strategy,
    )
