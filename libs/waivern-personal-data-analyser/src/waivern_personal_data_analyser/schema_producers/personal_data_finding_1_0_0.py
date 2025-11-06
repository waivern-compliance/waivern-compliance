"""Producer for personal_data_finding schema version 1.0.0."""

from typing import Any

from waivern_core.schemas import BaseAnalysisOutputMetadata

from waivern_personal_data_analyser.schemas.types import PersonalDataFindingModel


def produce(
    findings: list[PersonalDataFindingModel],
    summary: dict[str, Any],
    analysis_metadata: BaseAnalysisOutputMetadata,
    validation_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Transform internal result to personal_data_finding v1.0.0 format.

    Args:
        findings: List of validated PersonalDataFindingModel instances
        summary: Summary statistics dictionary
        analysis_metadata: Analysis metadata model
        validation_summary: Optional LLM validation summary (v1.0.0 includes this)

    Returns:
        Dictionary conforming to personal_data_finding v1.0.0 JSON schema

    """
    # Convert Pydantic models to dicts
    findings_dicts = [
        finding.model_dump(mode="json", exclude_none=True) for finding in findings
    ]

    # Build v1.0.0 output structure
    result: dict[str, Any] = {
        "findings": findings_dicts,
        "summary": summary,
        "analysis_metadata": analysis_metadata.model_dump(
            mode="json", exclude_none=True
        ),
    }

    # Include validation_summary if present (v1.0.0 supports this)
    if validation_summary:
        result["validation_summary"] = validation_summary

    return result
