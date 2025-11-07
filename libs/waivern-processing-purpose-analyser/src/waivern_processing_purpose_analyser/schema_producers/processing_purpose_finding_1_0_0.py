"""Producer for processing_purpose_finding schema version 1.0.0."""

from typing import Any

from waivern_core.schemas import BaseAnalysisOutputMetadata

from waivern_processing_purpose_analyser.schemas.types import (
    ProcessingPurposeFindingModel,
)


def produce(
    findings: list[ProcessingPurposeFindingModel],
    summary: dict[str, Any],
    analysis_metadata: BaseAnalysisOutputMetadata,
    validation_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Transform internal result to processing_purpose_finding v1.0.0 format.

    Args:
        findings: List of validated ProcessingPurposeFindingModel instances
        summary: Summary statistics dictionary
        analysis_metadata: Analysis metadata model
        validation_summary: Optional LLM validation summary statistics

    Returns:
        Dictionary conforming to processing_purpose_finding v1.0.0 JSON schema

    """
    # Convert Pydantic models to dicts
    findings_dicts = [
        finding.model_dump(mode="json", exclude_none=True) for finding in findings
    ]

    # Build v1.0.0 output structure
    result = {
        "findings": findings_dicts,
        "summary": summary,
        "analysis_metadata": analysis_metadata.model_dump(
            mode="json", exclude_none=True
        ),
    }

    # Add validation_summary if provided
    if validation_summary is not None:
        result["validation_summary"] = validation_summary

    return result
