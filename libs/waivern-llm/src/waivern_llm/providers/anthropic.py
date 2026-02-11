"""Anthropic LLM provider implementation."""

from __future__ import annotations

import asyncio
import logging
import os

from anthropic import AsyncAnthropic
from anthropic.types.beta.messages.batch_create_params import (
    Request as BatchRequestParams,
)
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, SecretStr

from waivern_llm.batch_types import BatchRequest, BatchSubmission
from waivern_llm.errors import LLMConfigurationError, LLMConnectionError
from waivern_llm.model_capabilities import ModelCapabilities
from waivern_llm.providers._schema_utils import ensure_strict_schema

logger = logging.getLogger(__name__)


class AnthropicProvider:
    """Anthropic Claude provider using LangChain and the Anthropic SDK.

    Provides async structured LLM calls (sync path via LangChain) and
    batch API operations (via the ``anthropic`` SDK's ``AsyncAnthropic``).
    Satisfies both the ``LLMProvider`` and ``BatchLLMProvider`` protocols.
    """

    _async_client: AsyncAnthropic | None = None

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

    # -------------------------------------------------------------------------
    # BatchLLMProvider protocol
    # -------------------------------------------------------------------------

    def _get_async_client(self) -> AsyncAnthropic:
        """Return the lazily-initialised ``AsyncAnthropic`` client.

        The sync path uses LangChain's ``ChatAnthropic`` and does not need this
        client. Creating it lazily avoids unnecessary overhead when only the
        sync path is used.
        """
        if self._async_client is None:
            self._async_client = AsyncAnthropic(api_key=self._api_key)
        return self._async_client

    async def submit_batch(self, requests: list[BatchRequest]) -> BatchSubmission:
        """Submit multiple prompts as a single batch.

        Builds a request list with structured output configuration and submits
        via the Anthropic Message Batches API.

        Args:
            requests: List of batch requests containing prompts and schemas.

        Returns:
            Confirmation with the provider's batch identifier and count.

        Raises:
            LLMConnectionError: If the submission request fails.

        """
        try:
            client = self._get_async_client()

            # Build request list
            request_list: list[BatchRequestParams] = []
            for request in requests:
                req_dict: BatchRequestParams = {
                    "custom_id": request.custom_id,
                    "params": {
                        "model": request.model,
                        "max_tokens": self._capabilities.max_output_tokens,
                        "temperature": self._capabilities.temperature,
                        "messages": [{"role": "user", "content": request.prompt}],
                        "output_format": {
                            "type": "json_schema",
                            "schema": ensure_strict_schema(request.response_schema),
                        },
                    },
                }
                request_list.append(req_dict)

            # Create batch using beta API
            # Note: We use the beta API because structured output (output_format)
            # is a beta feature. The standard messages.batches API does not support
            # the output_format field required for JSON schema responses.
            batch = await client.beta.messages.batches.create(requests=request_list)

            logger.info(f"Submitted batch {batch.id} with {len(requests)} request(s)")

            return BatchSubmission(
                batch_id=batch.id,
                request_count=len(requests),
            )

        except LLMConnectionError:
            raise
        except Exception as e:
            logger.error(f"Batch submission failed: {e}")
            raise LLMConnectionError(f"Batch submission failed: {e}") from e
