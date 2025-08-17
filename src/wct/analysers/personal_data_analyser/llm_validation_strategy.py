"""LLM validation strategy for personal data analysis."""

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from wct.analysers.runners.types import LLMValidationConfig
from wct.llm_service import AnthropicLLMService
from wct.prompts.personal_data_validation import (
    RecommendedAction,
    ValidationResult,
    extract_json_from_response,
    get_batch_validation_prompt,
)

from .types import PersonalDataFindingModel

logger = logging.getLogger(__name__)

# Private constants for validation logic
_DEFAULT_CONFIDENCE = 0.0
_DEFAULT_REASONING = "No reasoning provided"
_DEFAULT_ACTION = "keep"
_EMPTY_PROMPT_CONTENT = ""


class LLMValidationResultModel(BaseModel):
    """Strongly typed model for LLM validation results."""

    validation_result: str = Field(
        default="unknown", description="The validation result"
    )
    confidence: float = Field(
        default=_DEFAULT_CONFIDENCE,
        ge=0.0,
        le=1.0,
        description="Confidence score from LLM",
    )
    reasoning: str = Field(
        default=_DEFAULT_REASONING, description="Reasoning provided by LLM"
    )
    recommended_action: str = Field(
        default=_DEFAULT_ACTION, description="Recommended action from LLM"
    )


def personal_data_validation_strategy(
    findings: list[PersonalDataFindingModel],
    config: LLMValidationConfig,
    llm_service: AnthropicLLMService,
) -> list[PersonalDataFindingModel]:
    """LLM validation strategy for personal data findings.

    This strategy validates personal data findings using LLM to filter false positives.
    It processes findings in batches and uses specialized prompts for personal data validation.

    Args:
        findings: List of typed PersonalDataFindingModel objects to validate
        config: Configuration including batch_size, validation_mode, etc.
        llm_service: LLM service instance

    Returns:
        List of validated PersonalDataFindingModel objects with false positives removed

    """
    if not findings:
        logger.debug("No findings to validate")
        return findings

    # Process findings in batches - now working directly with typed objects
    validated_finding_objects = _process_findings_in_batches(
        findings, config, llm_service
    )

    logger.debug(
        f"Personal data validation completed: {len(findings)} → {len(validated_finding_objects)} findings"
    )

    return validated_finding_objects


def _process_findings_in_batches(
    finding_objects: list[PersonalDataFindingModel],
    config: LLMValidationConfig,
    llm_service: AnthropicLLMService,
) -> list[PersonalDataFindingModel]:
    """Process findings in batches for LLM validation.

    Args:
        finding_objects: List of PersonalDataFindingModel objects to validate
        config: LLM analysis runner configuration
        llm_service: LLM service instance

    Returns:
        List of validated PersonalDataFindingModel objects

    """
    batch_size = config.llm_batch_size
    validated_finding_objects: list[PersonalDataFindingModel] = []

    for i in range(0, len(finding_objects), batch_size):
        batch = finding_objects[i : i + batch_size]
        batch_results = _validate_findings_batch(batch, config, llm_service)
        validated_finding_objects.extend(batch_results)

    return validated_finding_objects


def _should_keep_finding(
    validation_result: str | None,
    action: str,
    finding: PersonalDataFindingModel,
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

    # Remove false positives
    if validation_result == ValidationResult.FALSE_POSITIVE:
        logger.info(
            f"Removed false positive: {finding.type} - {finding.matched_pattern} "
            f"(confidence: {confidence:.2f}) - {reasoning}"
        )
        return False

    # Handle edge cases - if uncertain, keep for safety
    logger.warning(
        f"Uncertain validation result for {finding.type}, keeping for safety: {reasoning}"
    )
    return True


def _validate_findings_batch(
    findings_batch: list[PersonalDataFindingModel],
    config: LLMValidationConfig,
    llm_service: AnthropicLLMService,
) -> list[PersonalDataFindingModel]:
    """Validate a batch of personal data findings using LLM.

    Args:
        findings_batch: Batch of findings to validate
        config: LLM analysis runner configuration
        llm_service: LLM service instance

    Returns:
        List of validated findings from this batch

    """
    try:
        # Convert findings to format expected by validation prompt
        findings_for_prompt = _convert_findings_for_prompt(findings_batch)

        # Generate validation prompt
        prompt = get_batch_validation_prompt(findings_for_prompt)

        # Get LLM validation response
        logger.debug(f"Validating batch of {len(findings_batch)} findings")
        response = llm_service.analyse_data(_EMPTY_PROMPT_CONTENT, prompt)

        # Extract and parse JSON response
        clean_json = extract_json_from_response(response)
        validation_results = json.loads(clean_json)

        # Filter findings based on validation results
        return _filter_findings_by_validation_results(
            findings_batch, validation_results
        )

    except Exception as e:
        logger.error(f"LLM validation failed for batch: {e}")
        logger.warning("Returning unvalidated findings due to LLM validation error")
        return findings_batch


def _convert_findings_for_prompt(
    findings_batch: list[PersonalDataFindingModel],
) -> list[dict[str, Any]]:
    """Convert PersonalDataFindingModel objects to format expected by validation prompt.

    Args:
        findings_batch: Batch of findings to convert

    Returns:
        List of finding dictionaries formatted for prompt

    """
    findings_for_prompt: list[dict[str, Any]] = []
    for finding in findings_batch:
        findings_for_prompt.append(
            {
                "type": finding.type,
                "risk_level": finding.risk_level,
                "special_category": finding.special_category,
                "matched_pattern": finding.matched_pattern,
                "evidence": finding.evidence,
                "metadata": finding.metadata,
            }
        )
    return findings_for_prompt


def _filter_findings_by_validation_results(
    findings_batch: list[PersonalDataFindingModel],
    validation_results: list[dict[str, Any]],
) -> list[PersonalDataFindingModel]:
    """Filter findings based on LLM validation results.

    Args:
        findings_batch: Original batch of findings
        validation_results: Validation results from LLM

    Returns:
        List of validated findings that should be kept

    """
    validated_findings: list[PersonalDataFindingModel] = []

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
            f"Finding '{finding.type}' ({finding.matched_pattern}): "
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
