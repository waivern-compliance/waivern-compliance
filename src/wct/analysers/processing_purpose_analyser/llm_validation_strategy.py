"""LLM validation strategy for processing purpose analysis."""

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from wct.analysers.types import LLMValidationConfig
from wct.llm_service import AnthropicLLMService
from wct.prompts.processing_purpose_validation import (
    RecommendedAction,
    ValidationResult,
    extract_json_from_response,
    get_processing_purpose_validation_prompt,
)

from .types import ProcessingPurposeFindingModel

logger = logging.getLogger(__name__)


class LLMValidationResultModel(BaseModel):
    """Strongly typed model for LLM validation results."""

    validation_result: str = Field(
        default="unknown", description="The validation result"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score from LLM",
    )
    reasoning: str = Field(
        default="No reasoning provided", description="Reasoning provided by LLM"
    )
    recommended_action: str = Field(
        default="keep", description="Recommended action from LLM"
    )


def processing_purpose_validation_strategy(
    findings: list[ProcessingPurposeFindingModel],
    config: LLMValidationConfig,
    llm_service: AnthropicLLMService,
) -> tuple[list[ProcessingPurposeFindingModel], bool]:
    """LLM validation strategy for processing purpose findings.

    This strategy validates processing purpose findings using LLM to filter false positives.
    It processes findings in batches and uses specialized prompts for processing purpose validation.

    Args:
        findings: List of typed ProcessingPurposeFindingModel objects to validate
        config: Configuration including batch_size, validation_mode, etc.
        llm_service: LLM service instance

    Returns:
        Tuple of (validated findings, validation_succeeded)

    """
    if not findings:
        logger.debug("No findings to validate")
        return findings, True

    try:
        # Process findings in batches - working directly with typed objects
        validated_finding_objects = _process_findings_in_batches(
            findings, config, llm_service
        )

        logger.debug(
            f"Processing purpose validation completed: {len(findings)} → {len(validated_finding_objects)} findings"
        )

        return validated_finding_objects, True

    except Exception as e:
        logger.error(f"LLM validation strategy failed: {e}")
        logger.warning("Returning original findings due to validation strategy error")
        return findings, False


def _process_findings_in_batches(
    finding_objects: list[ProcessingPurposeFindingModel],
    config: LLMValidationConfig,
    llm_service: AnthropicLLMService,
) -> list[ProcessingPurposeFindingModel]:
    """Process findings in batches for LLM validation.

    Args:
        finding_objects: List of ProcessingPurposeFindingModel objects to validate
        config: LLM analysis runner configuration
        llm_service: LLM service instance

    Returns:
        List of validated ProcessingPurposeFindingModel objects

    """
    batch_size = config.llm_batch_size
    validated_finding_objects: list[ProcessingPurposeFindingModel] = []

    for i in range(0, len(finding_objects), batch_size):
        batch = finding_objects[i : i + batch_size]
        batch_results = _validate_findings_batch(batch, config, llm_service)
        validated_finding_objects.extend(batch_results)

    return validated_finding_objects


def _should_keep_finding(
    validation_result: str | None,
    action: str,
    finding: ProcessingPurposeFindingModel,
    confidence: float,
    reasoning: str,
) -> bool:
    """Determine whether a finding should be kept based on validation results.

    Args:
        validation_result: LLM validation result
        action: Recommended action from LLM
        finding: The finding being evaluated
        confidence: Confidence score from LLM
        reasoning: Reasoning from LLM

    Returns:
        True if finding should be kept, False otherwise

    """
    # Keep findings that are validated as true positives
    if (
        validation_result == ValidationResult.TRUE_POSITIVE
        and action == RecommendedAction.KEEP
    ):
        return True

    # Keep findings flagged for review (conservative mode)
    if action == RecommendedAction.FLAG_FOR_REVIEW:
        return True

    # Remove false positives
    if validation_result == ValidationResult.FALSE_POSITIVE:
        logger.info(
            f"Removed false positive: {finding.purpose} - {finding.matched_pattern} "
            f"(confidence: {confidence:.2f}) - {reasoning}"
        )
        return False

    # Handle edge cases - if uncertain, keep for safety
    logger.warning(
        f"Uncertain validation result for {finding.purpose}, keeping for safety: {reasoning}"
    )
    return True


def _validate_findings_batch(
    findings_batch: list[ProcessingPurposeFindingModel],
    config: LLMValidationConfig,
    llm_service: AnthropicLLMService,
) -> list[ProcessingPurposeFindingModel]:
    """Validate a batch of processing purpose findings using LLM.

    Args:
        findings_batch: Batch of findings to validate
        config: LLM analysis runner configuration
        llm_service: LLM service instance

    Returns:
        List of validated findings from this batch

    """
    # Generate validation prompt using strongly-typed findings directly
    prompt = get_processing_purpose_validation_prompt(
        findings_batch, config.llm_validation_mode
    )

    # Get LLM validation response
    logger.debug(f"Validating batch of {len(findings_batch)} findings")
    response = llm_service.analyse_data("", prompt)

    # Extract and parse JSON response
    clean_json = extract_json_from_response(response)
    validation_results = json.loads(clean_json)

    # Filter findings based on validation results
    return _filter_findings_by_validation_results(findings_batch, validation_results)


def _filter_findings_by_validation_results(
    findings_batch: list[ProcessingPurposeFindingModel],
    validation_results: list[dict[str, Any]],
) -> list[ProcessingPurposeFindingModel]:
    """Filter findings based on LLM validation results.

    Args:
        findings_batch: Original batch of findings
        validation_results: Validation results from LLM

    Returns:
        List of validated findings that should be kept

    """
    validated_findings: list[ProcessingPurposeFindingModel] = []

    for i, result_data in enumerate(validation_results):
        if i >= len(findings_batch):
            logger.warning(
                f"Validation result index {i} exceeds batch size {len(findings_batch)}"
            )
            continue

        # Use strongly typed model for validation results
        try:
            result = LLMValidationResultModel.model_validate(result_data)
        except Exception as e:
            logger.warning(f"Failed to parse validation result {i}: {e}")
            # Use defaults for malformed results
            result = LLMValidationResultModel()

        finding = findings_batch[i]

        # Log validation decision
        logger.debug(
            f"Finding '{finding.purpose}' ({finding.matched_pattern}): "
            f"{result.validation_result} (confidence: {result.confidence:.2f}) - {result.reasoning}"
        )

        # Determine if finding should be kept
        if _should_keep_finding(
            result.validation_result,
            result.recommended_action,
            finding,
            result.confidence,
            result.reasoning,
        ):
            validated_findings.append(finding)

    return validated_findings
