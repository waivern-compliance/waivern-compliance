"""Google LLM provider implementation."""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os

from google import genai
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from waivern_llm.batch_types import (
    BatchRequest,
    BatchResult,
    BatchStatus,
    BatchStatusLiteral,
    BatchSubmission,
)
from waivern_llm.errors import LLMConfigurationError, LLMConnectionError
from waivern_llm.model_capabilities import ModelCapabilities
from waivern_llm.providers._schema_utils import convert_to_gemini_schema

logger = logging.getLogger(__name__)


class GoogleProvider:
    """Google Gemini provider using LangChain and the google-genai SDK.

    Provides async structured LLM calls (sync path via LangChain) and
    batch API operations (via the ``google-genai`` SDK's ``Client``).
    Satisfies both the ``LLMProvider`` and ``BatchLLMProvider`` protocols.
    """

    _genai_client: genai.Client | None = None

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

    # -------------------------------------------------------------------------
    # BatchLLMProvider protocol
    # -------------------------------------------------------------------------

    def _get_genai_client(self) -> genai.Client:
        """Return the lazily-initialised ``genai.Client``.

        The sync path uses LangChain's ``ChatGoogleGenerativeAI`` and does not
        need this client.  Creating it lazily avoids unnecessary overhead when
        only the sync path is used.
        """
        if self._genai_client is None:
            self._genai_client = genai.Client(api_key=self._api_key)
        return self._genai_client

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
            client = self._get_genai_client()

            # Build JSONL in-memory
            buf = io.BytesIO()
            for request in requests:
                line = {
                    "key": request.custom_id,
                    "request": {
                        "contents": [
                            {"role": "user", "parts": [{"text": request.prompt}]}
                        ],
                        "generation_config": {
                            "temperature": self._capabilities.temperature,
                            "max_output_tokens": self._capabilities.max_output_tokens,
                            "response_mime_type": "application/json",
                            "response_schema": convert_to_gemini_schema(
                                request.response_schema
                            ),
                        },
                    },
                }
                buf.write(json.dumps(line).encode("utf-8"))
                buf.write(b"\n")
            buf.seek(0)

            # Upload JSONL file
            uploaded = await client.aio.files.upload(  # type: ignore[reportUnknownMemberType]
                file=buf,
                config={"mime_type": "application/jsonl"},
            )

            # Create batch referencing the uploaded file
            batch_job = await client.aio.batches.create(  # type: ignore[reportUnknownMemberType]
                model=self._model,
                src=uploaded.name,  # type: ignore[reportArgumentType]
            )

            logger.info(
                f"Submitted batch {batch_job.name} with {len(requests)} request(s)"
            )

            return BatchSubmission(
                batch_id=batch_job.name or "",
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
            client = self._get_genai_client()
            batch_job = await client.aio.batches.get(name=batch_id)  # type: ignore[reportUnknownMemberType]

            state_value = batch_job.state.value if batch_job.state else ""
            status = _GEMINI_STATUS_MAP.get(state_value, "in_progress")

            return BatchStatus(
                batch_id=batch_id,
                status=status,
                completed_count=0,
                failed_count=0,
                total_count=0,
            )

        except LLMConnectionError:
            raise
        except Exception as e:
            logger.error(f"Batch status check failed: {e}")
            raise LLMConnectionError(f"Batch status check failed: {e}") from e

    async def get_batch_results(self, batch_id: str) -> list[BatchResult]:
        """Retrieve results for a completed batch.

        Downloads the output JSONL file from the Gemini Files API and parses
        each line into a ``BatchResult``.

        Args:
            batch_id: The provider's batch identifier from submission.

        Returns:
            Per-prompt results mapping back to cache keys via custom_id.

        Raises:
            LLMConnectionError: If the results request fails.

        """
        try:
            client = self._get_genai_client()
            batch_job = await client.aio.batches.get(name=batch_id)  # type: ignore[reportUnknownMemberType]

            file_name = batch_job.dest.file_name if batch_job.dest else None
            if not file_name:
                raise LLMConnectionError(
                    f"Batch {batch_id} has no output file. "
                    "The batch may not have completed successfully."
                )

            content: bytes = await client.aio.files.download(file=file_name)  # type: ignore[reportUnknownMemberType]
            results: list[BatchResult] = []

            for raw_line in content.decode("utf-8").strip().splitlines():
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
            client = self._get_genai_client()
            await client.aio.batches.cancel(name=batch_id)  # type: ignore[reportUnknownMemberType]
        except LLMConnectionError:
            raise
        except Exception as e:
            logger.error(f"Batch cancellation failed: {e}")
            raise LLMConnectionError(f"Batch cancellation failed: {e}") from e


_GEMINI_STATUS_MAP: dict[str, BatchStatusLiteral] = {
    "JOB_STATE_PENDING": "submitted",
    "JOB_STATE_QUEUED": "submitted",
    "JOB_STATE_RUNNING": "in_progress",
    "JOB_STATE_SUCCEEDED": "completed",
    "JOB_STATE_FAILED": "failed",
    "JOB_STATE_CANCELLING": "cancelled",
    "JOB_STATE_CANCELLED": "cancelled",
    "JOB_STATE_EXPIRED": "expired",
    "JOB_STATE_PARTIALLY_SUCCEEDED": "completed",
}


def _parse_batch_result_line(raw_line: str) -> BatchResult:
    """Parse a single JSONL line from a Gemini batch output file.

    Each line contains a response object with a ``key`` (mapping back to
    the cache key) and either a successful response or an error.
    """
    line = json.loads(raw_line)

    custom_id: str = line.get("key", "")

    # Check for error response
    if "error" in line and line["error"]:
        error = line["error"]
        message = error.get("message", str(error))
        return BatchResult(
            custom_id=custom_id,
            status="failed",
            response=None,
            error=message,
        )

    # Extract response text — Gemini returns candidates[].content.parts[].text
    try:
        response = line.get("response", line)
        candidates = response.get("candidates", [])
        text = candidates[0]["content"]["parts"][0]["text"]
        parsed = json.loads(text)
        return BatchResult(
            custom_id=custom_id,
            status="completed",
            response=parsed,
            error=None,
        )
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        return BatchResult(
            custom_id=custom_id,
            status="failed",
            response=None,
            error=f"Failed to parse response: {e}",
        )
