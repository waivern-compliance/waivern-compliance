"""OpenAI LLM provider implementation."""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
from typing import Any

from langchain_openai import ChatOpenAI
from openai import AsyncOpenAI
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

logger = logging.getLogger(__name__)


class OpenAIProvider:
    """OpenAI provider using LangChain and the OpenAI SDK.

    Provides async structured LLM calls (sync path via LangChain) and
    batch API operations (via the ``openai`` SDK's ``AsyncOpenAI``).
    Satisfies both the ``LLMProvider`` and ``BatchLLMProvider`` protocols.

    Supports custom base_url for OpenAI-compatible APIs (e.g., local LLMs).
    """

    _async_client: AsyncOpenAI | None = None

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
            temperature=self._capabilities.temperature,
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

    # -------------------------------------------------------------------------
    # BatchLLMProvider protocol
    # -------------------------------------------------------------------------

    def _get_async_client(self) -> AsyncOpenAI:
        """Return the lazily-initialised ``AsyncOpenAI`` client.

        The sync path uses LangChain's ``ChatOpenAI`` and does not need this
        client. Creating it lazily avoids unnecessary overhead when only the
        sync path is used.
        """
        if self._async_client is None:
            effective_api_key = self._api_key or "local"
            self._async_client = AsyncOpenAI(
                api_key=effective_api_key,
                base_url=self._base_url,
            )
        return self._async_client

    async def submit_batch(self, requests: list[BatchRequest]) -> BatchSubmission:
        """Submit multiple prompts as a single batch.

        Builds a JSONL file in-memory from the batch requests, uploads it
        via the Files API, then creates a batch referencing the uploaded file.

        Args:
            requests: List of batch requests containing prompts and schemas.

        Returns:
            Confirmation with the provider's batch identifier and count.

        Raises:
            LLMConnectionError: If the submission request fails.

        """
        try:
            client = self._get_async_client()

            # Build JSONL in-memory
            buf = io.BytesIO()
            for request in requests:
                line = {
                    "custom_id": request.custom_id,
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": request.model,
                        "messages": [{"role": "user", "content": request.prompt}],
                        "temperature": self._capabilities.temperature,
                        "max_completion_tokens": self._capabilities.max_output_tokens,
                        "response_format": {
                            "type": "json_schema",
                            "json_schema": {
                                "name": request.response_schema.get(
                                    "title", "response"
                                ),
                                "strict": True,
                                "schema": _ensure_strict_schema(
                                    request.response_schema
                                ),
                            },
                        },
                    },
                }
                buf.write(json.dumps(line).encode("utf-8"))
                buf.write(b"\n")
            buf.seek(0)

            # Upload JSONL file
            uploaded = await client.files.create(file=buf, purpose="batch")

            # Create batch
            batch = await client.batches.create(
                input_file_id=uploaded.id,
                endpoint="/v1/chat/completions",
                completion_window="24h",
            )

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
            batch = await client.batches.retrieve(batch_id)

            status = _OPENAI_STATUS_MAP.get(batch.status, "in_progress")

            completed_count = 0
            failed_count = 0
            total_count = 0
            if batch.request_counts is not None:
                completed_count = batch.request_counts.completed or 0
                failed_count = batch.request_counts.failed or 0
                total_count = batch.request_counts.total or 0

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

        Downloads the output file and parses each JSONL line into a
        ``BatchResult``, handling successful responses, per-line errors,
        and non-200 status codes.

        Args:
            batch_id: The provider's batch identifier from submission.

        Returns:
            Per-prompt results mapping back to cache keys via custom_id.

        Raises:
            LLMConnectionError: If the results request fails.

        """
        try:
            client = self._get_async_client()
            batch = await client.batches.retrieve(batch_id)
            results: list[BatchResult] = []

            # Both output and error files share the same JSONL structure
            file_ids = [
                fid
                for fid in (batch.output_file_id, batch.error_file_id)
                if fid is not None
            ]
            for file_id in file_ids:
                content = await client.files.content(file_id)
                for raw_line in content.text.strip().splitlines():
                    results.append(_parse_batch_result_line(raw_line))

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
            await client.batches.cancel(batch_id)
        except LLMConnectionError:
            raise
        except Exception as e:
            logger.error(f"Batch cancellation failed: {e}")
            raise LLMConnectionError(f"Batch cancellation failed: {e}") from e


_OPENAI_STATUS_MAP: dict[str, BatchStatusLiteral] = {
    "validating": "submitted",
    "in_progress": "in_progress",
    "finalizing": "in_progress",
    "completed": "completed",
    "failed": "failed",
    "expired": "expired",
    "cancelling": "cancelled",
    "cancelled": "cancelled",
}


def _parse_batch_result_line(raw_line: str) -> BatchResult:
    """Parse a single JSONL line from an OpenAI batch output or error file.

    Both files share the same structure. Each line contains:
    - ``custom_id``: the cache key
    - ``error``: top-level error (non-null when the request could not be dispatched)
    - ``response``: contains ``status_code`` and ``body`` with the completion or error detail
    """
    line = json.loads(raw_line)
    custom_id: str = line["custom_id"]

    if line.get("error"):
        return BatchResult(
            custom_id=custom_id,
            status="failed",
            response=None,
            error=line["error"].get("message", str(line["error"])),
        )

    response = line.get("response", {})
    http_ok = 200
    if response.get("status_code") != http_ok:
        body = response.get("body", {})
        error_detail = body.get("error", {})
        message = error_detail.get("message") if error_detail else None
        return BatchResult(
            custom_id=custom_id,
            status="failed",
            response=None,
            error=message or f"Non-200 status: {response.get('status_code')}",
        )

    body_content: str = response["body"]["choices"][0]["message"]["content"]
    parsed = json.loads(body_content)
    return BatchResult(
        custom_id=custom_id,
        status="completed",
        response=parsed,
        error=None,
    )


def _ensure_strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Add ``additionalProperties: false`` to all objects in a JSON schema.

    OpenAI's strict structured-output mode requires every object definition
    to include ``"additionalProperties": false``. Pydantic's
    ``model_json_schema()`` does not emit this by default.

    Operates recursively on the schema, including ``$defs`` and nested objects.
    Returns a new dict — the original is not mutated.
    """
    schema = dict(schema)

    if schema.get("type") == "object":
        schema["additionalProperties"] = False

    # Recurse into properties
    if "properties" in schema:
        schema["properties"] = {
            key: _ensure_strict_schema(value)  # type: ignore[arg-type]
            for key, value in schema["properties"].items()  # type: ignore[union-attr]
        }

    # Recurse into $defs (Pydantic puts referenced models here)
    if "$defs" in schema:
        schema["$defs"] = {
            key: _ensure_strict_schema(value)  # type: ignore[arg-type]
            for key, value in schema["$defs"].items()  # type: ignore[union-attr]
        }

    # Recurse into array items
    if "items" in schema and isinstance(schema["items"], dict):
        schema["items"] = _ensure_strict_schema(schema["items"])  # type: ignore[arg-type]

    return schema
