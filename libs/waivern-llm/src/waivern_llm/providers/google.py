"""Google LLM provider implementation."""

from __future__ import annotations

import asyncio
import logging
import os

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from waivern_llm.errors import LLMConfigurationError, LLMConnectionError
from waivern_llm.model_capabilities import ModelCapabilities

logger = logging.getLogger(__name__)


class GoogleProvider:
    """Google Gemini provider using LangChain.

    Provides async structured LLM calls using Google's Gemini models.
    Satisfies the LLMProvider protocol.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        """Initialise the Google provider.

        Args:
            api_key: Google API key. Falls back to GOOGLE_API_KEY env var.
            model: Model name. Falls back to GOOGLE_MODEL env var,
                   then defaults to gemini-2.5-flash.

        Raises:
            LLMConfigurationError: If API key is not provided or found in environment.

        """
        self._model = model or os.getenv("GOOGLE_MODEL") or "gemini-2.5-flash"
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY")

        if not self._api_key:
            raise LLMConfigurationError(
                "Google API key is required. Set GOOGLE_API_KEY environment "
                "variable or provide api_key parameter."
            )

        self._capabilities = ModelCapabilities.get(self._model)
        self._llm = ChatGoogleGenerativeAI(
            model=self._model,
            google_api_key=self._api_key,
            temperature=0,
            max_output_tokens=self._capabilities.max_output_tokens,
            timeout=300,
        )

        logger.info(f"Initialised Google provider with model: {self._model}")

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
