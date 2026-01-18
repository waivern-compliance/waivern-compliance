"""Base LLM service interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from langchain_core.messages import BaseMessage
from pydantic import BaseModel


class BaseLLMService(ABC):
    """Abstract base class for LLM service implementations.

    This class defines the interface that all LLM service providers must implement,
    enabling support for multiple providers (Anthropic, OpenAI, Google, etc.) with
    a unified interface for compliance analysis.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name being used.

        Used for context window auto-detection in token-aware batching.

        Returns:
            The model identifier string (e.g., "claude-sonnet-4-5-20250929").

        """
        pass

    @abstractmethod
    def invoke(self, prompt: str) -> str:
        """Invoke the LLM with a prompt and return the response as a string.

        Args:
            prompt: The prompt to send to the LLM

        Returns:
            LLM response as string

        Raises:
            LLMConnectionError: If LLM request fails

        """
        pass

    @abstractmethod
    def invoke_with_structured_output[T: BaseModel](
        self, prompt: str, output_schema: type[T]
    ) -> T:
        """Invoke LLM with structured output using a Pydantic schema.

        Uses LangChain's with_structured_output() to force the LLM to return
        data conforming to the provided Pydantic model. This eliminates the
        need for JSON parsing and extraction from free-form responses.

        Args:
            prompt: The prompt to send to the LLM
            output_schema: Pydantic model class defining the expected output structure

        Returns:
            Instance of the output_schema model populated with LLM response

        Raises:
            LLMConnectionError: If LLM request fails or response doesn't match schema

        """
        pass

    def _extract_content(self, response: BaseMessage) -> str:
        """Extract string content from LangChain response, handling all content types.

        LangChain responses can contain various content types. This method safely
        extracts text content regardless of the underlying structure.

        NOTE: LangChain's type definitions use Unknown types which cause basedpyright
        to report type errors. The logic below is sound and handles all possible
        content types properly, but type ignores are needed due to LangChain's
        incomplete type definitions.

        Args:
            response: LangChain BaseMessage response

        Returns:
            Extracted text content as string

        """
        content = response.content  # type: ignore[reportUnknownMemberType,reportUnknownVariableType]

        # Handle string content (most common case)
        if isinstance(content, str):
            return content.strip()

        # Handle list content (e.g., multiple text blocks)
        if isinstance(content, list):  # type: ignore[reportUnnecessaryIsInstance]
            text_parts: list[str] = []
            for item in content:  # type: ignore[reportUnknownVariableType]
                if isinstance(item, str):
                    text_parts.append(item)  # type: ignore[reportUnknownMemberType]
                elif isinstance(item, dict):  # type: ignore[reportUnnecessaryIsInstance]
                    # Extract text from dict structures (e.g., {"type": "text", "text": "content"})
                    if "text" in item:
                        text_parts.append(str(item["text"]))  # type: ignore[reportUnknownMemberType,reportUnknownArgumentType]
                    else:
                        # Fallback: convert entire dict to string
                        text_parts.append(str(item))  # type: ignore[reportUnknownMemberType,reportUnknownArgumentType]
                else:
                    # Fallback for any other type
                    text_parts.append(str(item))  # type: ignore[reportUnknownMemberType]
            return " ".join(text_parts).strip()  # type: ignore[reportUnknownArgumentType]

        # Handle dict content
        if isinstance(content, dict):  # type: ignore[reportUnnecessaryIsInstance]
            if "text" in content:
                return str(content["text"]).strip()  # type: ignore[reportUnknownArgumentType]
            else:
                # Fallback: convert entire dict to string
                return str(content).strip()

        # Final fallback for any other type
        return str(content).strip()
