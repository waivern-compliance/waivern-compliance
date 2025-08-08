"""LLM validation strategy for personal data analysis."""

import json
from logging import Logger
from typing import Any

from wct.logging import get_analyser_logger
from wct.prompts.personal_data_validation import (
    RecommendedAction,
    ValidationResult,
    extract_json_from_response,
    get_batch_validation_prompt,
)

from .types import PersonalDataFinding


def personal_data_validation_strategy(
    findings: list[dict[str, Any]], config: dict[str, Any], llm_service: Any
) -> list[dict[str, Any]]:
    """LLM validation strategy for personal data findings.

    This strategy validates personal data findings using LLM to filter false positives.
    It processes findings in batches and uses specialized prompts for personal data validation.

    Args:
        findings: List of personal data findings to validate
        config: Configuration including batch_size, validation_mode, etc.
        llm_service: LLM service instance

    Returns:
        List of validated findings with false positives removed
    """
    logger = get_analyser_logger("personal_data_validation")

    if not findings:
        logger.debug("No findings to validate")
        return findings

    # Convert dict findings to PersonalDataFinding objects for validation
    finding_objects = []
    for finding_dict in findings:
        finding_obj = PersonalDataFinding(
            type=finding_dict["type"],
            risk_level=finding_dict["risk_level"],
            special_category=finding_dict["special_category"],
            matched_pattern=finding_dict["matched_pattern"],
            evidence=finding_dict["evidence"],
            metadata=finding_dict["metadata"],
        )
        finding_objects.append(finding_obj)

    # Process findings in batches
    batch_size = config.get("llm_batch_size", 10)
    validated_finding_objects = []

    for i in range(0, len(finding_objects), batch_size):
        batch = finding_objects[i : i + batch_size]
        batch_results = _validate_findings_batch(batch, config, llm_service, logger)
        validated_finding_objects.extend(batch_results)

    # Convert back to dictionaries for the runner
    validated_findings = []
    for finding_obj in validated_finding_objects:
        validated_dict = {
            "type": finding_obj.type,
            "risk_level": finding_obj.risk_level,
            "special_category": finding_obj.special_category,
            "matched_pattern": finding_obj.matched_pattern,
            "evidence": finding_obj.evidence,
            "metadata": finding_obj.metadata,
        }
        validated_findings.append(validated_dict)

    logger.debug(
        f"Personal data validation completed: {len(findings)} → {len(validated_findings)} findings"
    )

    return validated_findings


def _validate_findings_batch(
    findings_batch: list[PersonalDataFinding],
    config: dict[str, Any],
    llm_service: Any,
    logger: Logger,
) -> list[PersonalDataFinding]:
    """Validate a batch of personal data findings using LLM.

    Args:
        findings_batch: Batch of findings to validate
        config: Configuration parameters
        llm_service: LLM service instance
        logger: Logger instance

    Returns:
        List of validated findings from this batch
    """
    try:
        # Convert findings to format expected by validation prompt
        findings_for_prompt = []
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

        # Generate validation prompt
        prompt = get_batch_validation_prompt(findings_for_prompt)

        # Get LLM validation response
        logger.debug(f"Validating batch of {len(findings_batch)} findings")
        response = llm_service.analyse_data("", prompt)

        # Extract and parse JSON response
        clean_json = extract_json_from_response(response)
        validation_results = json.loads(clean_json)

        # Filter findings based on validation results
        validated_findings = []
        for i, result in enumerate(validation_results):
            if i >= len(findings_batch):
                logger.warning(
                    f"Validation result index {i} exceeds batch size {len(findings_batch)}"
                )
                continue

            finding = findings_batch[i]
            validation_result = result.get("validation_result")
            confidence = result.get("confidence", 0.0)
            reasoning = result.get("reasoning", "No reasoning provided")
            action = result.get("recommended_action", "keep")

            # Log validation decision
            logger.debug(
                f"Finding '{finding.type}' ({finding.matched_pattern}): "
                f"{validation_result} (confidence: {confidence:.2f}) - {reasoning}"
            )

            # Keep findings that are validated as true positives
            if (
                validation_result == ValidationResult.TRUE_POSITIVE
                and action == RecommendedAction.KEEP
            ):
                validated_findings.append(finding)
            elif validation_result == ValidationResult.FALSE_POSITIVE:
                logger.info(
                    f"Removed false positive: {finding.type} - {finding.matched_pattern} "
                    f"(confidence: {confidence:.2f}) - {reasoning}"
                )
            else:
                # Handle edge cases - if uncertain, keep for safety
                logger.warning(
                    f"Uncertain validation result for {finding.type}, keeping for safety: {reasoning}"
                )
                validated_findings.append(finding)

        return validated_findings

    except Exception as e:
        logger.error(f"LLM validation failed for batch: {e}")
        logger.warning("Returning unvalidated findings due to LLM validation error")
        return findings_batch
