"""LLM service module for AI-powered compliance analysis."""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from typing import override

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage
from pydantic import SecretStr

from wct.errors import WCTError

logger = logging.getLogger(__name__)


class LLMServiceError(WCTError):
    """Base exception for LLM service related errors."""

    pass


class LLMConfigurationError(LLMServiceError):
    """Exception raised when LLM service is misconfigured."""

    pass


class LLMConnectionError(LLMServiceError):
    """Exception raised when LLM service connection fails."""

    pass


class BaseLLMService(ABC):
    """Abstract base class for LLM service implementations.

    This class defines the interface that all LLM service providers must implement,
    enabling support for multiple providers (Anthropic, OpenAI, Google, etc.) with
    a unified interface for compliance analysis.
    """

    @abstractmethod
    def analyse_data(self, text: str, analysis_prompt: str) -> str:
        """Analyse text using the LLM with a custom prompt.

        Args:
            text: The text content to analyse
            analysis_prompt: The prompt/instructions for analysis

        Returns:
            LLM analysis response as string

        Raises:
            LLMConnectionError: If LLM request fails

        """
        pass


class AnthropicLLMService(BaseLLMService):
    """Service for interacting with Anthropic's Claude models via LangChain.

    This service provides a unified interface for AI-powered compliance analysis
    using Anthropic's Claude models through the LangChain framework.
    """

    def __init__(
        self, model_name: str | None = None, api_key: str | None = None
    ) -> None:
        """Initialise the Anthropic LLM service.

        Args:
            model_name: The Anthropic model to use (will use ANTHROPIC_MODEL env var)
            api_key: Anthropic API key (will use ANTHROPIC_API_KEY env var if not provided)

        Raises:
            LLMConfigurationError: If API key is not provided or found in environment

        """
        # Get model name from parameter, environment, or default
        self.model_name = (
            model_name or os.getenv("ANTHROPIC_MODEL") or "claude-sonnet-4-5-20250929"
        )

        # Get API key from parameter or environment
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise LLMConfigurationError(
                "Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable "
                "or provide api_key parameter."
            )

        self._llm = None
        logger.info(f"Initialised Anthropic LLM service with model: {self.model_name}")

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

        """
        try:
            logger.debug(f"Analysing text (length: {len(text)} chars)")

            llm = self._get_llm()

            # Combine the analysis prompt with the text
            full_prompt = f"{analysis_prompt}\n\nText to analyse:\n{text}"

            response = llm.invoke(full_prompt)
            result = self._extract_content(response).strip()

            logger.debug(
                f"LLM analysis completed (response length: {len(result)} chars)"
            )

            return result

        except Exception as e:
            logger.error(f"Text analysis failed: {e}")
            raise LLMConnectionError(f"LLM text analysis failed: {e}") from e

    def _get_llm(self) -> ChatAnthropic:
        """Get or create the LangChain LLM instance.

        Returns:
            LangChain ChatAnthropic instance

        Raises:
            LLMConnectionError: If API key is not available

        """
        if self._llm is None:
            if not self._api_key:
                raise LLMConnectionError("API key is required but not available")

            self._llm = ChatAnthropic(
                model_name=self.model_name,
                api_key=SecretStr(self._api_key),
                temperature=0,  # Consistent responses for compliance analysis
                max_tokens_to_sample=8000,  # Adjust as needed for response length
                timeout=300,  # Increased timeout for LLM requests
                stop=None,  # Stop sequences for clean output
            )
            logger.debug("Created LangChain ChatAnthropic instance")

        return self._llm

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


class OpenAILLMService(BaseLLMService):
    """Service for interacting with OpenAI's models via LangChain.

    This service provides a unified interface for AI-powered compliance analysis
    using OpenAI's models (GPT-4, GPT-3.5, etc.) through the LangChain framework.
    """

    def __init__(
        self, model_name: str | None = None, api_key: str | None = None
    ) -> None:
        """Initialise the OpenAI LLM service.

        Args:
            model_name: The OpenAI model to use (will use OPENAI_MODEL env var)
            api_key: OpenAI API key (will use OPENAI_API_KEY env var if not provided)

        Raises:
            LLMConfigurationError: If API key is not provided or found in environment

        """
        # Get model name from parameter, environment, or default
        self.model_name = model_name or os.getenv("OPENAI_MODEL") or "gpt-4o"

        # Get API key from parameter or environment
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self._api_key:
            raise LLMConfigurationError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment variable "
                "or provide api_key parameter."
            )

        self._llm = None
        logger.info(f"Initialised OpenAI LLM service with model: {self.model_name}")

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
            LLMConfigurationError: If OpenAI provider is not installed

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

            if not self._api_key:
                raise LLMConnectionError("API key is required but not available")

            self._llm = ChatOpenAI(  # type: ignore[reportUnknownMemberType]
                model=self.model_name,
                api_key=SecretStr(self._api_key),
                temperature=0,  # Consistent responses for compliance analysis
                timeout=300,  # Increased timeout for LLM requests
            )
            logger.debug("Created LangChain ChatOpenAI instance")

        return self._llm  # type: ignore[return-value]

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
                    if "text" in item:
                        text_parts.append(str(item["text"]))  # type: ignore[reportUnknownMemberType,reportUnknownArgumentType]
                    else:
                        text_parts.append(str(item))  # type: ignore[reportUnknownMemberType,reportUnknownArgumentType]
                else:
                    text_parts.append(str(item))  # type: ignore[reportUnknownMemberType]
            return " ".join(text_parts).strip()  # type: ignore[reportUnknownArgumentType]

        # Handle dict content
        if isinstance(content, dict):  # type: ignore[reportUnnecessaryIsInstance]
            if "text" in content:
                return str(content["text"]).strip()  # type: ignore[reportUnknownArgumentType]
            else:
                return str(content).strip()

        # Final fallback for any other type
        return str(content).strip()


class LLMServiceFactory:
    """Factory for creating LLM service instances."""

    @staticmethod
    def create_anthropic_service(
        model_name: str | None = None, api_key: str | None = None
    ) -> AnthropicLLMService:
        """Create an Anthropic LLM service instance.

        Args:
            model_name: The Anthropic model to use (uses ANTHROPIC_MODEL env var or default if not provided)
            api_key: Optional API key (uses ANTHROPIC_API_KEY env var if not provided)

        Returns:
            Configured AnthropicLLMService instance

        """
        return AnthropicLLMService(model_name=model_name, api_key=api_key)

    @staticmethod
    def create_openai_service(
        model_name: str | None = None, api_key: str | None = None
    ) -> OpenAILLMService:
        """Create an OpenAI LLM service instance.

        Args:
            model_name: The OpenAI model to use (uses OPENAI_MODEL env var or default if not provided)
            api_key: Optional API key (uses OPENAI_API_KEY env var if not provided)

        Returns:
            Configured OpenAILLMService instance

        """
        return OpenAILLMService(model_name=model_name, api_key=api_key)
