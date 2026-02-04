"""Anthropic LLM provider implementation."""

from __future__ import annotations

import asyncio
import logging
import os

from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, SecretStr

from waivern_llm.errors import LLMConfigurationError, LLMConnectionError
from waivern_llm.model_capabilities import ModelCapabilities

logger = logging.getLogger(__name__)


class AnthropicProvider:
    """Anthropic Claude provider using LangChain.

    Provides async structured LLM calls using Anthropic's Claude models.
    Satisfies the LLMProvider protocol.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        """Initialise the Anthropic provider.

        Args:
            api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
            model: Model name. Falls back to ANTHROPIC_MODEL env var,
                   then defaults to claude-sonnet-4-5.

        Raises:
            LLMConfigurationError: If API key is not provided or found in environment.

        """
        self._model = model or os.getenv("ANTHROPIC_MODEL") or "claude-sonnet-4-5"
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

        if not self._api_key:
            raise LLMConfigurationError(
                "Anthropic API key is required. Set ANTHROPIC_API_KEY environment "
                "variable or provide api_key parameter."
            )

        self._capabilities = ModelCapabilities.get(self._model)
        self._llm = ChatAnthropic(
            model_name=self._model,
            api_key=SecretStr(self._api_key),
            temperature=0,  # Consistent responses for compliance analysis
            max_tokens_to_sample=self._capabilities.max_output_tokens,
            timeout=300,
            stop=None,
        )

        logger.info(f"Initialised Anthropic provider with model: {self._model}")

    @property
    def model_name(self) -> str:
        """Return the model name being used."""
        return self._model

    @property
    def context_window(self) -> int:
        """Return the model's context window size in tokens."""
        return self._capabilities.context_window

    async def invoke_structured[R: BaseModel](
        self, prompt: str, response_model: type[R]
    ) -> R:
        """Invoke the LLM with structured output.

        Args:
            prompt: The prompt to send to the LLM.
            response_model: Pydantic model class defining expected output structure.

        Returns:
            Instance of response_model populated with the LLM response.

        Raises:
            LLMConnectionError: If the LLM request fails.

        """
        try:
            logger.debug(f"Invoking structured output: {response_model.__name__}")

            structured_llm = self._llm.with_structured_output(response_model)  # type: ignore[reportUnknownMemberType]

            # LangChain is sync, so wrap in asyncio.to_thread
            result = await asyncio.to_thread(structured_llm.invoke, prompt)  # type: ignore[reportUnknownMemberType,reportUnknownVariableType]

            logger.debug("Structured output invocation completed")
            return result  # type: ignore[reportReturnType]

        except Exception as e:
            logger.error(f"Structured output invocation failed: {e}")
            raise LLMConnectionError(f"LLM structured output failed: {e}") from e
