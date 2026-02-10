"""LLM service exceptions."""

from waivern_core.errors import PendingProcessingError, WaivernError


class LLMServiceError(WaivernError):
    """Base exception for LLM service related errors."""

    pass


class LLMConfigurationError(LLMServiceError):
    """Exception raised when LLM service is misconfigured."""

    pass


class LLMConnectionError(LLMServiceError):
    """Exception raised when LLM service connection fails."""

    pass


class PendingBatchError(LLMServiceError, PendingProcessingError):
    """Raised when LLM prompts have been submitted to a batch API and results are not yet available.

    The DAGExecutor catches this to leave the artifact in ``not_started``
    and mark the run as ``interrupted``. On resume, the artifact is
    re-attempted and the cache provides the completed batch results.
    """

    def __init__(self, *, run_id: str, batch_ids: list[str]) -> None:
        """Initialise with the run ID and list of pending batch IDs."""
        self.run_id = run_id
        self.batch_ids = batch_ids
        super().__init__(
            f"Batch results pending for run {run_id} "
            f"({len(batch_ids)} batch(es) submitted)"
        )
