"""Producer for data_subject_finding schema version 1.0.0."""

from datetime import UTC, datetime
from typing import Any

from waivern_core.schemas import BaseAnalysisOutputMetadata

from waivern_community.analysers.data_subject_analyser.schemas.types import (
    DataSubjectFindingModel,
)


def produce(
    findings: list[DataSubjectFindingModel],
    summary: dict[str, Any],
    analysis_metadata: BaseAnalysisOutputMetadata,
) -> dict[str, Any]:
    """Transform internal result to data_subject_finding v1.0.0 format.

    Args:
        findings: List of validated DataSubjectFindingModel instances
        summary: Summary statistics dictionary
        analysis_metadata: Analysis metadata model

    Returns:
        Dictionary conforming to data_subject_finding v1.0.0 JSON schema

    """
    # Convert Pydantic models to dicts
    findings_dicts = [
        finding.model_dump(mode="json", exclude_none=True) for finding in findings
    ]

    # Convert metadata to dict and add schema-required timestamp
    metadata_dict = analysis_metadata.model_dump(mode="json", exclude_none=True)
    metadata_dict["analysis_timestamp"] = datetime.now(UTC).isoformat()

    # Build v1.0.0 output structure
    return {
        "findings": findings_dicts,
        "summary": summary,
        "analysis_metadata": metadata_dict,
    }
