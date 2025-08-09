"""Base interface for analysis runners."""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class AnalysisRunner(ABC, Generic[T]):
    """Base interface for analysis runners that perform specific analysis processes.

    Analysis runners are responsible for executing complete analysis processes,
    such as pattern matching, LLM validation, or classification. Each runner
    manages its own dependencies and utilities.

    Runners are designed to be:
    - Self-contained: Manage their own dependencies
    - Reusable: Can be used by multiple analysers
    - Testable: Can be tested independently
    - Composable: Can be combined in different ways
    """

    @abstractmethod
    def get_analysis_type(self) -> str:
        """Return the type of analysis this runner performs.

        This is used to identify the runner and for logging purposes.

        Returns:
            String identifier for this analysis type (e.g., "pattern_matching", "llm_validation")
        """
        pass

    @abstractmethod
    def run_analysis(
        self, input_data: Any, metadata: dict[str, Any], config: dict[str, Any]
    ) -> list[T]:
        """Run the complete analysis process.

        Args:
            input_data: The data to analyze (type depends on the specific runner)
            metadata: Metadata about the input data
            config: Configuration parameters for the analysis

        Returns:
            List of analysis results (type depends on the specific runner)

        Raises:
            AnalysisRunnerError: If the analysis process fails
        """
        pass


class AnalysisRunnerError(Exception):
    """Base exception for analysis runner errors."""

    def __init__(
        self, runner_type: str, message: str, original_error: Exception | None = None
    ):
        """Initialise the error.

        Args:
            runner_type: The type of runner that failed
            message: Error message
            original_error: The original exception that caused this error
        """
        self.runner_type = runner_type
        self.original_error = original_error
        super().__init__(f"[{runner_type}] {message}")
