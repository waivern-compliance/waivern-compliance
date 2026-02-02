"""OpenAI LLM provider implementation."""

from __future__ import annotations

import asyncio
import logging
import os

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, SecretStr

from waivern_llm.errors import LLMConfigurationError, LLMConnectionError
from waivern_llm.model_capabilities import ModelCapabilities

logger = logging.getLogger(__name__)


class OpenAIProvider:
    """OpenAI provider using LangChain.

    Provides async structured LLM calls using OpenAI's models.
    Satisfies the LLMProvider protocol.

    Supports custom base_url for OpenAI-compatible APIs (e.g., local LLMs).
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        """Initialise the OpenAI provider.

        Args:
            api_key: OpenAI API key. Falls back to OPENAI_API_KEY env var.
                     Optional when base_url is set (for local LLMs).
            model: Model name. Falls back to OPENAI_MODEL env var,
                   then defaults to gpt-4o.
            base_url: Base URL for OpenAI-compatible APIs. Falls back to
                      OPENAI_BASE_URL env var.

        Raises:
            LLMConfigurationError: If API key is not provided and base_url is not set.

        """
        self._model = model or os.getenv("OPENAI_MODEL") or "gpt-4o"
        self._base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")

        if not self._api_key and not self._base_url:
            raise LLMConfigurationError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment "
                "variable or provide api_key parameter. "
                "For local LLMs, set OPENAI_BASE_URL instead."
            )

        self._capabilities = ModelCapabilities.get(self._model)

        # API key placeholder for local LLMs (LangChain requires it but servers ignore it)
        effective_api_key = self._api_key or "local"

        self._llm = ChatOpenAI(
            model=self._model,
            api_key=SecretStr(effective_api_key),
            base_url=self._base_url,
            temperature=0,
            max_tokens=self._capabilities.max_output_tokens,  # type: ignore[reportCallIssue]
            timeout=300,
        )

        logger.info(f"Initialised OpenAI provider with model: {self._model}")

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
            result = await asyncio.to_thread(structured_llm.invoke, prompt)  # type: ignore[reportUnknownMemberType,reportUnknownVariableType]

            logger.debug("Structured output invocation completed")
            return result  # type: ignore[reportReturnType]

        except Exception as e:
            logger.error(f"Structured output invocation failed: {e}")
            raise LLMConnectionError(f"LLM structured output failed: {e}") from e
