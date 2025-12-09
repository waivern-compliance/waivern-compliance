"""Protocol for compliance exporters."""

from typing import Any, Protocol

from waivern_orchestration import ExecutionPlan, ExecutionResult


class Exporter(Protocol):
    """Protocol for compliance exporters.

    Exporters are configured at instantiation with their specific requirements,
    then used to export execution results. This keeps the protocol generic while
    allowing each exporter to have strongly-typed configuration.
    """

    @property
    def name(self) -> str:
        """Exporter identifier (e.g., 'json', 'gdpr', 'ccpa')."""
        ...

    @property
    def supported_frameworks(self) -> list[str]:
        """Compliance frameworks this exporter handles.

        Returns:
            Empty list: Generic exporter (handles any framework)
            Non-empty: Only these frameworks (e.g., ["GDPR", "UK_GDPR"])

        """
        ...

    def validate(
        self,
        result: ExecutionResult,
        plan: ExecutionPlan,
    ) -> list[str]:
        """Validate that result meets exporter requirements.

        Each exporter implements its own validation logic to check
        that the ExecutionResult contains the necessary data.

        Args:
            result: Execution result to validate
            plan: Execution plan with artifact definitions

        Returns:
            List of validation errors (empty if valid)

        """
        ...

    def export(
        self,
        result: ExecutionResult,
        plan: ExecutionPlan,
    ) -> dict[str, Any]:
        """Export execution results to structured format.

        Args:
            result: Execution results with artifact data
            plan: Execution plan with runbook metadata

        Returns:
            Export dictionary ready for JSON serialisation

        """
        ...
