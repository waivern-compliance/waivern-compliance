"""Anthropic LLM service implementation."""

from __future__ import annotations

import logging
import os
from typing import override

from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, SecretStr

from waivern_llm.base import BaseLLMService
from waivern_llm.errors import LLMConfigurationError, LLMConnectionError
from waivern_llm.model_capabilities import ModelCapabilities

logger = logging.getLogger(__name__)


class AnthropicLLMService(BaseLLMService):
    """Service for interacting with Anthropic's Claude models via LangChain.

    This service provides a unified interface for AI-powered compliance analysis
    using Anthropic's Claude models through the LangChain framework.
    """

    def __init__(
        self,
        model_name: str | None = None,
        api_key: str | None = None,
        capabilities: ModelCapabilities | None = None,
    ) -> None:
        """Initialise the Anthropic LLM service.

        Args:
            model_name: The Anthropic model to use (will use ANTHROPIC_MODEL env var)
            api_key: Anthropic API key (will use ANTHROPIC_API_KEY env var if not provided)
            capabilities: Model capabilities override. If None, auto-detected from model name.

        Raises:
            LLMConfigurationError: If API key is not provided or found in environment

        """
        # Get model name from parameter, environment, or default
        self._model_name = (
            model_name or os.getenv("ANTHROPIC_MODEL") or "claude-sonnet-4-5-20250929"
        )

        # Get API key from parameter or environment
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise LLMConfigurationError(
                "Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable "
                "or provide api_key parameter."
            )

        # Get capabilities from parameter or auto-detect from model name
        self._capabilities = capabilities or ModelCapabilities.get(self._model_name)

        self._llm = None
        logger.info(f"Initialised Anthropic LLM service with model: {self._model_name}")

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

        """
        try:
            logger.debug(f"Invoking LLM (prompt length: {len(prompt)} chars)")

            llm = self._get_llm()
            response = llm.invoke(prompt)
            result = self._extract_content(response).strip()

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

            llm = self._get_llm()
            structured_llm = llm.with_structured_output(output_schema)  # type: ignore[reportUnknownMemberType]
            result = structured_llm.invoke(prompt)  # type: ignore[reportUnknownMemberType,reportUnknownVariableType]

            logger.debug("Structured output invocation completed")
            return result  # type: ignore[reportReturnType]

        except Exception as e:
            logger.error(f"Structured output invocation failed: {e}")
            raise LLMConnectionError(f"LLM structured output failed: {e}") from e

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
                max_tokens_to_sample=self._capabilities.max_output_tokens,
                timeout=300,  # Increased timeout for LLM requests
                stop=None,  # Stop sequences for clean output
            )
            logger.debug("Created LangChain ChatAnthropic instance")

        return self._llm
