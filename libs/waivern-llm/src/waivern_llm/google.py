"""Google LLM service implementation."""

from __future__ import annotations

import logging
import os
from typing import override

from waivern_llm.base import BaseLLMService
from waivern_llm.errors import LLMConfigurationError, LLMConnectionError

logger = logging.getLogger(__name__)


class GoogleLLMService(BaseLLMService):
    """Service for interacting with Google's Gemini models via LangChain.

    This service provides a unified interface for AI-powered compliance analysis
    using Google's Gemini models through the LangChain framework.
    """

    def __init__(
        self, model_name: str | None = None, api_key: str | None = None
    ) -> None:
        """Initialise the Google LLM service.

        Args:
            model_name: The Google model to use (will use GOOGLE_MODEL env var)
            api_key: Google API key (will use GOOGLE_API_KEY env var if not provided)

        Raises:
            LLMConfigurationError: If API key is not provided or found in environment

        """
        # Get model name from parameter, environment, or default
        self.model_name = model_name or os.getenv("GOOGLE_MODEL") or "gemini-2.5-flash"

        # Get API key from parameter or environment
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self._api_key:
            raise LLMConfigurationError(
                "Google API key is required. Set GOOGLE_API_KEY environment variable "
                "or provide api_key parameter."
            )

        self._llm = None
        logger.info(f"Initialised Google LLM service with model: {self.model_name}")

    @override
    def analyse_data(self, text: str, analysis_prompt: str) -> str:
        """Analyse text using the LLM with a custom prompt.

        Args:
            text: The text content to analyse
            analysis_prompt: The prompt/instructions for analysis

        Returns:
            LLM analysis response as string

        Raises:
            LLMConnectionError: If LLM request fails
            LLMConfigurationError: If Google provider is not installed

        """
        try:
            logger.debug(f"Analysing text (length: {len(text)} chars)")

            llm = self._get_llm()  # type: ignore[reportUnknownMemberType]

            # Combine the analysis prompt with the text
            full_prompt = f"{analysis_prompt}\n\nText to analyse:\n{text}"

            response = llm.invoke(full_prompt)  # type: ignore[reportUnknownMemberType,reportUnknownVariableType]
            result = self._extract_content(response).strip()  # type: ignore[reportUnknownArgumentType]

            logger.debug(
                f"LLM analysis completed (response length: {len(result)} chars)"
            )

            return result

        except Exception as e:
            logger.error(f"Text analysis failed: {e}")
            raise LLMConnectionError(f"LLM text analysis failed: {e}") from e

    def _get_llm(self) -> ChatGoogleGenerativeAI:  # type: ignore[name-defined] # noqa: F821
        """Get or create the LangChain LLM instance with lazy import.

        NOTE: This method uses lazy imports and type ignores because langchain-google-genai
        is an optional dependency. The type ignores are necessary due to:
        1. ChatGoogleGenerativeAI not being available at type checking time (optional dependency)
        2. Intentional lazy import pattern (PLC0415) for optional dependencies
        This is the same pattern used throughout the codebase for optional dependencies.

        Returns:
            LangChain ChatGoogleGenerativeAI instance

        Raises:
            LLMConfigurationError: If langchain-google-genai is not installed
            LLMConnectionError: If API key is not available

        """
        if self._llm is None:  # type: ignore[reportUnknownMemberType]
            # Lazy import with helpful error message
            try:
                from langchain_google_genai import (  # noqa: PLC0415  # type: ignore[reportMissingImports]
                    ChatGoogleGenerativeAI,  # type: ignore[reportUnknownVariableType]
                )
            except ImportError as e:
                raise LLMConfigurationError(
                    "Google provider is not installed.\n"
                    "Install it with: uv sync --group llm-google\n"
                    "Or install all providers: uv sync --group llm-all"
                ) from e

            if not self._api_key:
                raise LLMConnectionError("API key is required but not available")

            self._llm = ChatGoogleGenerativeAI(  # type: ignore[reportUnknownMemberType]
                model=self.model_name,
                google_api_key=self._api_key,
                temperature=0,  # Consistent responses for compliance analysis
                timeout=300,  # Increased timeout for LLM requests
            )
            logger.debug("Created LangChain ChatGoogleGenerativeAI instance")

        return self._llm  # type: ignore[return-value]
