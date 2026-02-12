"""Anthropic LLM provider implementation."""

from __future__ import annotations

import asyncio
import json
import logging
import os

from anthropic import AsyncAnthropic
from anthropic.types.beta.beta_text_block import BetaTextBlock
from anthropic.types.beta.messages.batch_create_params import (
    Request as BatchRequestParams,
)
from anthropic.types.beta.messages.beta_message_batch_canceled_result import (
    BetaMessageBatchCanceledResult,
)
from anthropic.types.beta.messages.beta_message_batch_errored_result import (
    BetaMessageBatchErroredResult,
)
from anthropic.types.beta.messages.beta_message_batch_succeeded_result import (
    BetaMessageBatchSucceededResult,
)
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, SecretStr

from waivern_llm.batch_types import (
    BatchRequest,
    BatchResult,
    BatchStatus,
    BatchStatusLiteral,
    BatchSubmission,
)
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
            # Note: SDK type stubs for output_config are incomplete/outdated.
            # The API accepts output_config.format but types don't reflect this yet.
            request_list: list[BatchRequestParams] = []
            for request in requests:
                req_dict = {
                    "custom_id": request.custom_id,
                    "params": {
                        "model": request.model,
                        "max_tokens": self._capabilities.max_output_tokens,
                        "temperature": self._capabilities.temperature,
                        "messages": [{"role": "user", "content": request.prompt}],
                        "output_config": {
                            "format": {
                                "type": "json_schema",
                                "schema": ensure_strict_schema(request.response_schema),
                            }
                        },
                    },
                }
                request_list.append(req_dict)  # type: ignore[reportArgumentType]

            # Create batch using beta API
            # Note: We use the beta API because structured output (output_config)
            # is a beta feature. The standard messages.batches API does not support
            # the output_config field required for JSON schema responses.
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

    async def get_batch_status(self, batch_id: str) -> BatchStatus:
        """Poll a batch's processing status.

        Args:
            batch_id: The provider's batch identifier from submission.

        Returns:
            Current status including completion and failure counts.

        Raises:
            LLMConnectionError: If the status request fails.

        """
        try:
            client = self._get_async_client()
            batch = await client.beta.messages.batches.retrieve(batch_id)

            status = _ANTHROPIC_STATUS_MAP.get(batch.processing_status, "in_progress")

            # Map Anthropic's request counts to our schema
            counts = batch.request_counts
            completed_count = counts.succeeded or 0
            failed_count = (
                (counts.errored or 0) + (counts.expired or 0) + (counts.canceled or 0)
            )
            total_count = (
                (counts.processing or 0)
                + (counts.succeeded or 0)
                + (counts.errored or 0)
                + (counts.canceled or 0)
                + (counts.expired or 0)
            )

            return BatchStatus(
                batch_id=batch_id,
                status=status,
                completed_count=completed_count,
                failed_count=failed_count,
                total_count=total_count,
            )

        except LLMConnectionError:
            raise
        except Exception as e:
            logger.error(f"Batch status check failed: {e}")
            raise LLMConnectionError(f"Batch status check failed: {e}") from e

    async def get_batch_results(self, batch_id: str) -> list[BatchResult]:
        """Retrieve results for a completed batch.

        Streams results from the Anthropic Message Batches API and parses each
        result type (succeeded, errored, canceled, expired) into a BatchResult.

        Args:
            batch_id: The provider's batch identifier from submission.

        Returns:
            Per-prompt results mapping back to cache keys via custom_id.

        Raises:
            LLMConnectionError: If the results request fails.

        """
        try:
            client = self._get_async_client()
            results: list[BatchResult] = []

            # Stream results from the beta API
            result_stream = await client.beta.messages.batches.results(batch_id)
            async for response in result_stream:
                custom_id = response.custom_id
                result = response.result

                if isinstance(result, BetaMessageBatchSucceededResult):
                    # Extract JSON from message content
                    # For structured output, the first content block is a TextBlock
                    content_block = result.message.content[0]
                    if isinstance(content_block, BetaTextBlock):
                        message_content = content_block.text
                        parsed = json.loads(message_content)
                        results.append(
                            BatchResult(
                                custom_id=custom_id,
                                status="completed",
                                response=parsed,
                                error=None,
                            )
                        )
                    else:
                        # Unexpected content block type for structured output
                        results.append(
                            BatchResult(
                                custom_id=custom_id,
                                status="failed",
                                response=None,
                                error=f"Unexpected content block type: {type(content_block).__name__}",
                            )
                        )
                elif isinstance(result, BetaMessageBatchErroredResult):
                    # BetaErrorResponse wraps BetaError in a response envelope
                    results.append(
                        BatchResult(
                            custom_id=custom_id,
                            status="failed",
                            response=None,
                            error=result.error.error.message,
                        )
                    )
                elif isinstance(result, BetaMessageBatchCanceledResult):
                    results.append(
                        BatchResult(
                            custom_id=custom_id,
                            status="failed",
                            response=None,
                            error="Request was cancelled",
                        )
                    )
                else:  # BetaMessageBatchExpiredResult
                    results.append(
                        BatchResult(
                            custom_id=custom_id,
                            status="failed",
                            response=None,
                            error="Request expired",
                        )
                    )

            return results

        except LLMConnectionError:
            raise
        except Exception as e:
            logger.error(f"Batch results retrieval failed: {e}")
            raise LLMConnectionError(f"Batch results retrieval failed: {e}") from e

    async def cancel_batch(self, batch_id: str) -> None:
        """Cancel an in-progress batch.

        Args:
            batch_id: The provider's batch identifier from submission.

        Raises:
            LLMConnectionError: If the cancellation request fails.

        """
        try:
            client = self._get_async_client()
            _ = await client.beta.messages.batches.cancel(batch_id)
        except LLMConnectionError:
            raise
        except Exception as e:
            logger.error(f"Batch cancellation failed: {e}")
            raise LLMConnectionError(f"Batch cancellation failed: {e}") from e


_ANTHROPIC_STATUS_MAP: dict[str, BatchStatusLiteral] = {
    "in_progress": "in_progress",
    "canceling": "cancelled",
    "ended": "completed",
}
