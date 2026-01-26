"""OpenAI LLM service implementation."""

from __future__ import annotations

import logging
import os
from typing import override

from pydantic import BaseModel, SecretStr

from waivern_llm.base import BaseLLMService
from waivern_llm.errors import LLMConfigurationError, LLMConnectionError

logger = logging.getLogger(__name__)


class OpenAILLMService(BaseLLMService):
    """Service for interacting with OpenAI's models via LangChain.

    This service provides a unified interface for AI-powered compliance analysis
    using OpenAI's models (GPT-4, GPT-3.5, etc.) through the LangChain framework.
    """

    def __init__(
        self,
        model_name: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        """Initialise the OpenAI LLM service.

        Args:
            model_name: The OpenAI model to use (will use OPENAI_MODEL env var)
            api_key: OpenAI API key (will use OPENAI_API_KEY env var if not provided)
            base_url: Base URL for OpenAI-compatible APIs (e.g., local LLMs).
                     Will use OPENAI_BASE_URL env var if not provided.

        Raises:
            LLMConfigurationError: If API key is not provided and base_url is not set

        """
        # Get model name from parameter, environment, or default
        self._model_name = model_name or os.getenv("OPENAI_MODEL") or "gpt-4o"

        # Get base URL from parameter or environment (for local LLMs)
        self._base_url = base_url or os.getenv("OPENAI_BASE_URL")

        # Get API key from parameter or environment
        # API key is optional when base_url is set (local LLMs don't need it)
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self._api_key and not self._base_url:
            raise LLMConfigurationError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment variable "
                "or provide api_key parameter. "
                "For local LLMs, set OPENAI_BASE_URL instead."
            )

        self._llm = None
        logger.info(f"Initialised OpenAI LLM service with model: {self._model_name}")

    @property
    @override
    def model_name(self) -> str:
        """Return the model name being used."""
        return self._model_name

    @override
    def invoke(self, prompt: str) -> str:
        """Invoke the LLM with a prompt and return the response as a string.

        Args:
            prompt: The prompt to send to the LLM

        Returns:
            LLM response as string

        Raises:
            LLMConnectionError: If LLM request fails
            LLMConfigurationError: If OpenAI provider is not installed

        """
        try:
            logger.debug(f"Invoking LLM (prompt length: {len(prompt)} chars)")

            llm = self._get_llm()  # type: ignore[reportUnknownMemberType]
            response = llm.invoke(prompt)  # type: ignore[reportUnknownMemberType,reportUnknownVariableType]
            result = self._extract_content(response).strip()  # type: ignore[reportUnknownArgumentType]

            logger.debug(
                f"LLM invocation completed (response length: {len(result)} chars)"
            )

            return result

        except Exception as e:
            logger.error(f"LLM invocation failed: {e}")
            raise LLMConnectionError(f"LLM invocation failed: {e}") from e

    @override
    def invoke_with_structured_output[T: BaseModel](
        self, prompt: str, output_schema: type[T]
    ) -> T:
        """Invoke LLM with structured output using a Pydantic schema.

        Uses LangChain's with_structured_output() to force the LLM to return
        data conforming to the provided Pydantic model.

        Args:
            prompt: The prompt to send to the LLM
            output_schema: Pydantic model class defining the expected output structure

        Returns:
            Instance of the output_schema model populated with LLM response

        Raises:
            LLMConnectionError: If LLM request fails or response doesn't match schema

        """
        try:
            logger.debug(f"Invoking with structured output: {output_schema.__name__}")

            llm = self._get_llm()  # type: ignore[reportUnknownMemberType]
            structured_llm = llm.with_structured_output(output_schema)  # type: ignore[reportUnknownMemberType]
            result = structured_llm.invoke(prompt)  # type: ignore[reportUnknownMemberType,reportUnknownVariableType]

            logger.debug("Structured output invocation completed")
            return result  # type: ignore[reportReturnType]

        except Exception as e:
            logger.error(f"Structured output invocation failed: {e}")
            raise LLMConnectionError(f"LLM structured output failed: {e}") from e

    def _get_llm(self) -> ChatOpenAI:  # type: ignore[name-defined] # noqa: F821
        """Get or create the LangChain LLM instance with lazy import.

        NOTE: This method uses lazy imports and type ignores because langchain-openai
        is an optional dependency. The type ignores are necessary due to:
        1. ChatOpenAI not being available at type checking time (optional dependency)
        2. Intentional lazy import pattern (PLC0415) for optional dependencies
        This is the same pattern used throughout the codebase for optional dependencies.

        Returns:
            LangChain ChatOpenAI instance

        Raises:
            LLMConfigurationError: If langchain-openai is not installed
            LLMConnectionError: If API key is not available

        """
        if self._llm is None:  # type: ignore[reportUnknownMemberType]
            # Lazy import with helpful error message
            try:
                from langchain_openai import (  # noqa: PLC0415  # type: ignore[reportMissingImports]
                    ChatOpenAI,  # type: ignore[reportUnknownVariableType]
                )
            except ImportError as e:
                raise LLMConfigurationError(
                    "OpenAI provider is not installed.\n"
                    "Install it with: uv sync --group llm-openai\n"
                    "Or install all providers: uv sync --group llm-all"
                ) from e

            # API key is required for cloud OpenAI, optional for local LLMs
            if not self._api_key and not self._base_url:
                raise LLMConnectionError("API key is required but not available")

            # LangChain requires api_key even for local LLMs, but local servers ignore it
            # Use "local" as placeholder when base_url is set but api_key is not
            effective_api_key = self._api_key or "local"

            self._llm = ChatOpenAI(  # type: ignore[reportUnknownMemberType]
                model=self.model_name,
                api_key=SecretStr(effective_api_key),
                base_url=self._base_url,
                temperature=0,  # Consistent responses for compliance analysis
                timeout=300,  # Increased timeout for LLM requests
            )
            logger.debug("Created LangChain ChatOpenAI instance")

        return self._llm  # type: ignore[return-value]
