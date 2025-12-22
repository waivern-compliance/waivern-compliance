"""Core export functionality shared by all exporters."""

from typing import Any, Literal

from pydantic import BaseModel, Field
from waivern_orchestration import ExecutionPlan, ExecutionResult


class SchemaInfo(BaseModel):
    """Schema information for output entries."""

    name: str = Field(..., description="Schema name")
    version: str = Field(..., description="Schema version")


class OutputEntry(BaseModel):
    """Output entry for a single artifact."""

    artifact_id: str = Field(..., description="Artifact identifier")
    duration_seconds: float = Field(..., ge=0, description="Execution time in seconds")
    name: str | None = Field(None, description="Optional artifact name")
    description: str | None = Field(None, description="Optional artifact description")
    contact: str | None = Field(None, description="Optional artifact contact")
    output_schema: SchemaInfo | None = Field(
        None, description="Output schema information", alias="schema"
    )
    content: dict[str, Any] | None = Field(None, description="Artifact output content")


class ErrorEntry(BaseModel):
    """Error entry for a failed artifact."""

    artifact_id: str = Field(..., description="Artifact identifier")
    error: str = Field(..., description="Error message")


class RunInfo(BaseModel):
    """Information about the execution run."""

    id: str = Field(..., description="Unique run identifier (UUID)")
    timestamp: str = Field(..., description="ISO8601 timestamp with timezone")
    duration_seconds: float = Field(..., ge=0, description="Total execution time")
    status: Literal["completed", "partial", "failed"] = Field(
        ..., description="Execution status"
    )


class RunbookInfo(BaseModel):
    """Information about the runbook."""

    name: str = Field(..., description="Runbook name")
    description: str = Field(..., description="Runbook description")
    contact: str | None = Field(None, description="Optional runbook contact")


class SummaryInfo(BaseModel):
    """Summary statistics for the execution."""

    total: int = Field(..., ge=0, description="Total number of artifacts")
    succeeded: int = Field(..., ge=0, description="Number of successful artifacts")
    failed: int = Field(..., ge=0, description="Number of failed artifacts")
    skipped: int = Field(..., ge=0, description="Number of skipped artifacts")


class CoreExport(BaseModel):
    """Core export format shared by all exporters.

    This model defines the standard export structure that all exporters
    produce or extend. It provides runtime validation and clear documentation
    of the export format.
    """

    format_version: Literal["2.0.0"] = Field(..., description="Export format version")
    run: RunInfo = Field(..., description="Execution run information")
    runbook: RunbookInfo = Field(..., description="Runbook metadata")
    summary: SummaryInfo = Field(..., description="Execution summary statistics")
    outputs: list[OutputEntry] = Field(
        default_factory=list, description="Output entries for artifacts"
    )
    errors: list[ErrorEntry] = Field(
        default_factory=list, description="Error entries for failed artifacts"
    )
    skipped: list[str] = Field(
        default_factory=list, description="IDs of skipped artifacts"
    )


def _calculate_status(
    result: ExecutionResult,
) -> Literal["completed", "partial", "failed"]:
    """Calculate execution status from result.

    Args:
        result: Execution result with artifact outcomes.

    Returns:
        Status string: "failed" if any failures, "partial" if skipped, else "completed".

    """
    has_failures = any(not msg.is_success for msg in result.artifacts.values())
    has_skipped = len(result.skipped) > 0

    if has_failures:
        return "failed"
    elif has_skipped:
        return "partial"
    else:
        return "completed"


def _build_error_entries(result: ExecutionResult) -> list[ErrorEntry]:
    """Build error entries from failed artifacts.

    Args:
        result: Execution result with artifact outcomes.

    Returns:
        List of ErrorEntry for failed artifacts.

    """
    return [
        ErrorEntry(artifact_id=art_id, error=msg.execution_error or "Unknown error")
        for art_id, msg in result.artifacts.items()
        if not msg.is_success
    ]


def _build_skipped_list(result: ExecutionResult) -> list[str]:
    """Build skipped artifact ID list.

    Args:
        result: Execution result with artifact outcomes.

    Returns:
        List of skipped artifact IDs.

    """
    return list(result.skipped)


def _calculate_summary(result: ExecutionResult) -> SummaryInfo:
    """Calculate summary statistics.

    Args:
        result: Execution result with artifact outcomes.

    Returns:
        Summary statistics for the execution.

    """
    succeeded = sum(1 for msg in result.artifacts.values() if msg.is_success)
    failed = sum(1 for msg in result.artifacts.values() if not msg.is_success)
    skipped = len(result.skipped)
    total = len(result.artifacts) + skipped

    return SummaryInfo(
        total=total,
        succeeded=succeeded,
        failed=failed,
        skipped=skipped,
    )


def _build_output_entries(
    result: ExecutionResult, plan: ExecutionPlan
) -> list[OutputEntry]:
    """Build output entries for artifacts marked output:true.

    Args:
        result: Execution result with artifact outcomes.
        plan: Execution plan with runbook and schemas.

    Returns:
        List of OutputEntry for artifacts marked for output.

    """
    outputs: list[OutputEntry] = []

    for art_id, message in result.artifacts.items():
        # Only include successful artifacts marked output:true
        artifact_def = plan.runbook.artifacts.get(art_id)
        if not artifact_def or not artifact_def.output or not message.is_success:
            continue

        # Get schema info from plan
        _, output_schema = plan.artifact_schemas.get(art_id, (None, None))
        schema_info = (
            SchemaInfo(name=output_schema.name, version=output_schema.version)
            if output_schema
            else None
        )

        # Build output entry with artifact metadata
        outputs.append(
            OutputEntry(
                artifact_id=art_id,
                duration_seconds=message.execution_duration or 0.0,
                name=artifact_def.name,
                description=artifact_def.description,
                contact=artifact_def.contact,
                schema=schema_info,
                content=message.content if message.content else None,
            )
        )

    return outputs


def build_core_export(result: ExecutionResult, plan: ExecutionPlan) -> CoreExport:
    """Build core export format shared by all exporters.

    Args:
        result: Execution result with artifact outcomes.
        plan: Execution plan with runbook metadata.

    Returns:
        Validated CoreExport model with standard structure.

    """
    return CoreExport(
        format_version="2.0.0",
        run=RunInfo(
            id=result.run_id,
            timestamp=result.start_timestamp,
            duration_seconds=result.total_duration_seconds,
            status=_calculate_status(result),
        ),
        runbook=RunbookInfo(
            name=plan.runbook.name,
            description=plan.runbook.description,
            contact=plan.runbook.contact,
        ),
        summary=_calculate_summary(result),
        errors=_build_error_entries(result),
        skipped=_build_skipped_list(result),
        outputs=_build_output_entries(result, plan),
    )
