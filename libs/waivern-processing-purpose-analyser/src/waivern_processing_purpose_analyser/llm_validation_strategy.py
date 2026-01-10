"""LLM validation strategy for processing purpose analysis."""

import logging
from typing import Any, override

from waivern_analysers_shared.llm_validation import (
    LLMValidationStrategy,
)
from waivern_analysers_shared.llm_validation.token_estimation import (
    calculate_max_payload_tokens,
    get_model_context_window,
)
from waivern_analysers_shared.types import LLMBatchingStrategy, LLMValidationConfig
from waivern_llm import BaseLLMService
from waivern_source_code_analyser import (
    SourceCodeDataModel,
    SourceCodeFileContentProvider,
)

from waivern_processing_purpose_analyser.prompts.processing_purpose_validation import (
    get_processing_purpose_validation_prompt,
)

from .batched_files_validation_strategy import ProcessingPurposeBatchedFilesStrategy
from .schemas.types import ProcessingPurposeFindingModel

logger = logging.getLogger(__name__)


class ProcessingPurposeValidationStrategy(
    LLMValidationStrategy[ProcessingPurposeFindingModel]
):
    """LLM validation strategy for processing purpose findings."""

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

    @override
    def convert_findings_for_prompt(
        self, findings_batch: list[ProcessingPurposeFindingModel]
    ) -> list[dict[str, Any]]:
        """Convert ProcessingPurposeFindingModel objects to format expected by validation prompt."""
        return [finding.model_dump() for finding in findings_batch]


def processing_purpose_validation_strategy(
    findings: list[ProcessingPurposeFindingModel],
    config: LLMValidationConfig,
    llm_service: BaseLLMService,
    source_data: SourceCodeDataModel | None = None,
) -> tuple[list[ProcessingPurposeFindingModel], bool]:
    """LLM validation strategy for processing purpose findings.

    This strategy validates processing purpose findings using LLM to filter false positives.
    Supports two batching strategies:
    - BATCH_FINDINGS (default): Batches by finding count with evidence snippets
    - BATCH_FILES: Batches by file with full file content (when source_data provided)

    Args:
        findings: List of typed ProcessingPurposeFindingModel objects to validate
        config: Configuration including batch_size, validation_mode, batching_strategy
        llm_service: LLM service instance
        source_data: Optional source code data for file-based batching

    Returns:
        Tuple of (validated findings, validation_succeeded)

    """
    # Use file-based batching if configured and source data is available
    if (
        config.llm_batching_strategy == LLMBatchingStrategy.BATCH_FILES
        and source_data is not None
    ):
        logger.info("Using file-based batching strategy for LLM validation")
        return _validate_with_file_batching(findings, config, llm_service, source_data)

    # Default: use finding-based batching
    strategy = ProcessingPurposeValidationStrategy()
    return strategy.validate_findings(findings, config, llm_service)


def _validate_with_file_batching(
    findings: list[ProcessingPurposeFindingModel],
    config: LLMValidationConfig,
    llm_service: BaseLLMService,
    source_data: SourceCodeDataModel,
) -> tuple[list[ProcessingPurposeFindingModel], bool]:
    """Validate findings using file-based batching with full file content.

    Args:
        findings: Findings to validate.
        config: LLM validation configuration.
        llm_service: LLM service for validation calls.
        source_data: Source code data model with file contents.

    Returns:
        Tuple of (validated findings, validation_succeeded).

    """
    # Calculate max tokens per batch
    context_window = config.batching.model_context_window
    if context_window is None:
        # Auto-detect from model name (all concrete LLM services have model_name attribute)
        model_name = str(getattr(llm_service, "model_name", ""))
        context_window = get_model_context_window(model_name)
        logger.debug(f"Auto-detected context window: {context_window} tokens")

    max_tokens = calculate_max_payload_tokens(context_window)
    logger.debug(f"Max tokens per batch: {max_tokens}")

    # Create file content provider and strategy
    file_provider = SourceCodeFileContentProvider(source_data)
    strategy = ProcessingPurposeBatchedFilesStrategy()

    return strategy.validate_findings_with_file_content(
        findings=findings,
        file_provider=file_provider,
        max_tokens_per_batch=max_tokens,
        llm_service=llm_service,
    )
