"""JSON exporter for generic compliance analysis results."""

from typing import Any

from waivern_artifact_store import ArtifactStore
from waivern_orchestration import ExecutionPlan, ExecutionResult

from wct.exporters.core import build_core_export


class JsonExporter:
    """Generic JSON exporter - formats any framework."""

    @property
    def name(self) -> str:
        """Return exporter identifier."""
        return "json"

    @property
    def supported_frameworks(self) -> list[str]:
        """Return supported compliance frameworks.

        Returns:
            Empty list - JsonExporter is framework-agnostic and handles any framework.

        """
        return []

    def validate(
        self,
        result: ExecutionResult,
        plan: ExecutionPlan,
    ) -> list[str]:
        """Validate that result meets exporter requirements.

        JsonExporter accepts any result structure (no validation needed).

        Args:
            result: Execution result to validate
            plan: Execution plan with artifact definitions

        Returns:
            Empty list - always valid

        """
        return []

    async def export(
        self,
        result: ExecutionResult,
        plan: ExecutionPlan,
        store: ArtifactStore,
    ) -> dict[str, Any]:
        """Export execution results to JSON-serializable dictionary.

        Args:
            result: Execution results with artifact data
            plan: Execution plan with runbook metadata
            store: Artifact store to load artifact messages

        Returns:
            Dictionary with CoreExport structure, ready for JSON serialization

        """
        core_export = await build_core_export(result, plan, store)
        return core_export.model_dump()
