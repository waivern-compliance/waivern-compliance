"""LLM validation strategy for processing purpose analysis."""

import logging
from typing import override

from waivern_analysers_shared.llm_validation import (
    DefaultLLMValidationStrategy,
)
from waivern_analysers_shared.llm_validation.token_estimation import (
    calculate_max_payload_tokens,
    get_model_context_window,
)
from waivern_analysers_shared.types import LLMBatchingStrategy, LLMValidationConfig
from waivern_core.message import Message
from waivern_llm import BaseLLMService
from waivern_source_code_analyser import (
    SourceCodeDataModel,
    SourceCodeFileContentProvider,
)

from waivern_processing_purpose_analyser.prompts.processing_purpose_validation import (
    get_processing_purpose_validation_prompt,
)

from .batched_files_validation_strategy import ProcessingPurposeBatchedFilesStrategy
from .schemas.types import (
    ProcessingPurposeFindingMetadata,
    ProcessingPurposeFindingModel,
)

logger = logging.getLogger(__name__)

# Validation mark key for findings that passed LLM validation
_VALIDATION_MARK_KEY = "processing_purpose_llm_validated"


class ProcessingPurposeValidationStrategy(
    DefaultLLMValidationStrategy[ProcessingPurposeFindingModel]
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


def processing_purpose_validation_strategy(
    findings: list[ProcessingPurposeFindingModel],
    config: LLMValidationConfig,
    llm_service: BaseLLMService,
    input_message: Message,
) -> tuple[list[ProcessingPurposeFindingModel], bool]:
    """LLM validation strategy for processing purpose findings.

    This strategy validates processing purpose findings using LLM to filter false positives.
    Supports two batching strategies:
    - BATCH_FINDINGS (default): Batches by finding count with evidence snippets
    - BATCH_FILES: Batches by file with full file content (for source_code schema)

    Args:
        findings: List of typed ProcessingPurposeFindingModel objects to validate
        config: Configuration including batch_size, validation_mode, batching_strategy
        llm_service: LLM service instance
        input_message: Input message (strategy determines batching approach from schema)

    Returns:
        Tuple of (validated findings, validation_succeeded)

    """
    # Use file-based batching if configured and input is source_code schema
    if (
        config.llm_batching_strategy == LLMBatchingStrategy.BATCH_FILES
        and input_message.schema.name == "source_code"
    ):
        logger.info("Using file-based batching strategy for LLM validation")
        source_data = SourceCodeDataModel.model_validate(input_message.content)
        return _validate_with_file_batching(findings, config, llm_service, source_data)

    # Default: use finding-based batching
    strategy = ProcessingPurposeValidationStrategy()
    validated_findings, succeeded = strategy.validate_findings(
        findings, config, llm_service
    )

    # Mark all validated findings
    marked_findings = [_mark_finding_as_validated(f) for f in validated_findings]
    return marked_findings, succeeded


def _validate_with_file_batching(
    findings: list[ProcessingPurposeFindingModel],
    config: LLMValidationConfig,
    llm_service: BaseLLMService,
    source_data: SourceCodeDataModel,
) -> tuple[list[ProcessingPurposeFindingModel], bool]:
    """Validate findings using file-based batching with full file content.

    For findings that can't use file-based batching (oversized/missing files),
    falls back to finding-based validation. All validated findings are marked
    with metadata.context["processing_purpose_llm_validated"] = True.

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

    # Run file-based validation
    result = strategy.validate_findings_with_file_content(
        findings=findings,
        file_provider=file_provider,
        max_tokens_per_batch=max_tokens,
        llm_service=llm_service,
        validation_mode=config.llm_validation_mode,
    )

    # Mark file-validated findings
    validated_findings = [
        _mark_finding_as_validated(f) for f in result.validated_findings
    ]
    all_succeeded = result.all_batches_succeeded

    # Fallback to finding-based validation for unvalidated findings
    if result.unvalidated_findings:
        logger.info(
            f"Falling back to finding-based validation for "
            f"{len(result.unvalidated_findings)} findings"
        )
        fallback_strategy = ProcessingPurposeValidationStrategy()
        fallback_validated, fallback_succeeded = fallback_strategy.validate_findings(
            result.unvalidated_findings, config, llm_service
        )
        # Mark fallback-validated findings
        validated_findings.extend(
            _mark_finding_as_validated(f) for f in fallback_validated
        )
        all_succeeded = all_succeeded and fallback_succeeded

    return validated_findings, all_succeeded


def _mark_finding_as_validated(
    finding: ProcessingPurposeFindingModel,
) -> ProcessingPurposeFindingModel:
    """Mark a finding as LLM validated by setting metadata context flag.

    Creates metadata if not present. Returns a new finding with the mark.
    """
    if finding.metadata is None:
        # Create metadata with validation mark (source="composition" indicates pipeline-created)
        new_metadata = ProcessingPurposeFindingMetadata(
            source="composition",
            context={_VALIDATION_MARK_KEY: True},
        )
    else:
        # Add mark to existing context
        new_context = dict(finding.metadata.context)
        new_context[_VALIDATION_MARK_KEY] = True
        new_metadata = finding.metadata.model_copy(update={"context": new_context})

    return finding.model_copy(update={"metadata": new_metadata})
