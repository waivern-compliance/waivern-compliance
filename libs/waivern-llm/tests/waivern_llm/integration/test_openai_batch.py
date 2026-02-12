"""Integration tests for OpenAI batch API operations.

These tests make real API calls to OpenAI's Batch API and may take
several minutes to complete (batch processing is asynchronous).

Run with: uv run pytest -m batch
"""

import asyncio

import pytest
from waivern_core import JsonValue

from waivern_llm.batch_types import BatchRequest
from waivern_llm.providers import OpenAIProvider

from .conftest import (
    POLL_INTERVAL_SECONDS,
    POLL_TIMEOUT_SECONDS,
    VALIDATION_PROMPT,
    ValidationResponse,
)


@pytest.mark.integration
@pytest.mark.batch
class TestOpenAIBatchIntegration:
    """End-to-end tests for OpenAI BatchLLMProvider methods."""

    async def test_submit_poll_and_retrieve_batch_results(
        self, require_openai_api_key: str
    ) -> None:
        """Full flow: submit batch, poll until completed, retrieve and verify results."""
        provider = OpenAIProvider(api_key=require_openai_api_key, model="gpt-5-mini")

        schema: dict[str, JsonValue] = ValidationResponse.model_json_schema()
        requests = [
            BatchRequest(
                custom_id="integration-test-key-1",
                prompt=VALIDATION_PROMPT,
                model="gpt-5-mini",
                response_schema=schema,
            ),
        ]

        # Submit
        submission = await provider.submit_batch(requests)
        assert submission.batch_id
        assert submission.request_count == 1

        # Poll until completed or timeout
        status = await provider.get_batch_status(submission.batch_id)
        elapsed = 0
        while status.status not in ("completed", "failed", "expired", "cancelled"):
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            elapsed += POLL_INTERVAL_SECONDS
            if elapsed >= POLL_TIMEOUT_SECONDS:
                break
            status = await provider.get_batch_status(submission.batch_id)

        assert status.status == "completed", (
            f"Batch did not complete within {POLL_TIMEOUT_SECONDS}s "
            f"(final status: {status.status})"
        )

        # Retrieve results
        results = await provider.get_batch_results(submission.batch_id)
        assert len(results) == 1

        result = results[0]
        assert result.custom_id == "integration-test-key-1"
        assert result.status == "completed"
        assert result.response is not None

        # Verify the response can be parsed as our ValidationResponse
        parsed = ValidationResponse.model_validate(result.response)
        assert len(parsed.results) == 1
        assert parsed.results[0].finding_id == "finding-001"
        assert parsed.results[0].validation_result in (
            "TRUE_POSITIVE",
            "FALSE_POSITIVE",
        )

    async def test_cancel_batch(self, require_openai_api_key: str) -> None:
        """Submit a batch then immediately cancel it."""
        provider = OpenAIProvider(api_key=require_openai_api_key, model="gpt-5-mini")

        schema: dict[str, JsonValue] = ValidationResponse.model_json_schema()
        requests = [
            BatchRequest(
                custom_id="integration-test-cancel-1",
                prompt=VALIDATION_PROMPT,
                model="gpt-5-mini",
                response_schema=schema,
            ),
        ]

        # Submit
        submission = await provider.submit_batch(requests)

        # Immediately cancel
        await provider.cancel_batch(submission.batch_id)

        # Poll to verify the batch transitions to a terminal state
        status = await provider.get_batch_status(submission.batch_id)
        elapsed = 0
        while status.status not in ("completed", "cancelled", "failed", "expired"):
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            elapsed += POLL_INTERVAL_SECONDS
            if elapsed >= POLL_TIMEOUT_SECONDS:
                break
            status = await provider.get_batch_status(submission.batch_id)

        # Accept either cancelled or completed (batch may have finished before cancel)
        assert status.status in ("cancelled", "completed"), (
            f"Batch did not reach terminal state within {POLL_TIMEOUT_SECONDS}s "
            f"(final status: {status.status})"
        )
