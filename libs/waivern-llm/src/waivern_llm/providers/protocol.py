"""LLM provider protocols.

Defines the contracts that LLM providers must satisfy:

- ``LLMProvider`` — synchronous structured output (required for all providers)
- ``BatchLLMProvider`` — asynchronous batch API operations (optional)

A provider can implement both protocols or just ``LLMProvider``.
"""

from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from waivern_llm.batch_types import (
    BatchRequest,
    BatchResult,
    BatchStatus,
    BatchSubmission,
)


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM providers.

    Providers implement this protocol to integrate with the LLM service.
    The service uses providers to make structured LLM calls with automatic
    batching and caching.

    Properties:
        model_name: Model identifier used for context window auto-detection.
        context_window: Maximum tokens the model can process in one request.

    The protocol is runtime_checkable to allow isinstance() verification,
    which is useful for validation and testing.
    """

    @property
    def model_name(self) -> str:
        """Return the model name being used.

        Used for logging and context window auto-detection when not
        explicitly provided.

        Returns:
            Model identifier string (e.g., "claude-sonnet-4-5-20250929").

        """
        ...

    @property
    def context_window(self) -> int:
        """Return the model's context window size in tokens.

        Used by the batch planner to calculate maximum payload sizes
        and perform token-aware bin-packing.

        Returns:
            Maximum tokens the model can process in one request.

        """
        ...

    async def invoke_structured[R: BaseModel](
        self, prompt: str, response_model: type[R]
    ) -> R:
        """Invoke the LLM with structured output.

        Calls the LLM and returns a response conforming to the provided
        Pydantic model schema.

        Args:
            prompt: The prompt to send to the LLM.
            response_model: Pydantic model class defining expected output structure.

        Returns:
            Instance of response_model populated with the LLM response.

        Raises:
            LLMConnectionError: If the LLM request fails.

        """
        ...


@runtime_checkable
class BatchLLMProvider(Protocol):
    """Protocol for providers that support asynchronous batch APIs.

    Batch-capable providers implement this protocol alongside ``LLMProvider``
    to enable bulk prompt submission.  The ``DefaultLLMService`` checks at
    runtime via ``isinstance(provider, BatchLLMProvider)`` to decide between
    the synchronous and batch code paths.

    Not all providers support batch mode — implementing this protocol is
    optional.  A provider that only implements ``LLMProvider`` will always
    use the synchronous path.
    """

    async def submit_batch(self, requests: list[BatchRequest]) -> BatchSubmission:
        """Submit multiple prompts as a single batch.

        Args:
            requests: List of batch requests, each containing a prompt,
                model identifier, and custom_id (cache key).

        Returns:
            Confirmation with the provider's batch identifier and count.

        Raises:
            LLMConnectionError: If the submission request fails.

        """
        ...

    async def get_batch_status(self, batch_id: str) -> BatchStatus:
        """Poll a batch's processing status.

        Args:
            batch_id: The provider's batch identifier from submission.

        Returns:
            Current status including completion and failure counts.

        Raises:
            LLMConnectionError: If the status request fails.

        """
        ...

    async def get_batch_results(self, batch_id: str) -> list[BatchResult]:
        """Retrieve results for a completed batch.

        Should only be called after ``get_batch_status`` reports the batch
        as completed.

        Args:
            batch_id: The provider's batch identifier from submission.

        Returns:
            Per-prompt results mapping back to cache keys via custom_id.

        Raises:
            LLMConnectionError: If the results request fails.

        """
        ...

    async def cancel_batch(self, batch_id: str) -> None:
        """Cancel an in-progress batch.

        Args:
            batch_id: The provider's batch identifier from submission.

        Raises:
            LLMConnectionError: If the cancellation request fails.

        """
        ...
