"""LLMProvider protocol for v2 LLM service.

Defines the contract that all v2 LLM providers must satisfy.
"""

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for v2 LLM providers.

    Providers implement this protocol to integrate with the v2 LLM service.
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
