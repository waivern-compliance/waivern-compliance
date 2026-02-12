"""Integration tests for Anthropic batch API operations.

These tests make real API calls to Anthropic's Message Batches API and may take
several minutes to complete (batch processing is asynchronous).

Run with: uv run pytest -m batch
"""

import asyncio
from typing import Literal

import pytest
from pydantic import BaseModel, Field
from waivern_core import JsonValue

from waivern_llm.batch_types import BatchRequest
from waivern_llm.providers import AnthropicProvider

POLL_INTERVAL_SECONDS = 10
POLL_TIMEOUT_SECONDS = 300  # 5 minutes


class ValidationResult(BaseModel):
    """Single validation result — mirrors real analyser response models."""

    finding_id: str = Field(description="ID of the finding being validated")
    validation_result: Literal["TRUE_POSITIVE", "FALSE_POSITIVE"] = Field(
        description="Whether the finding is a true or false positive"
    )
    confidence: float = Field(description="Confidence score between 0 and 1")
    reasoning: str = Field(description="Explanation for the validation decision")


class ValidationResponse(BaseModel):
    """Batch validation response — mirrors LLMValidationResponseModel."""

    results: list[ValidationResult] = Field(
        description="List of validation results for each finding"
    )


VALIDATION_PROMPT = """\
You are a compliance data validator. Analyse the following finding and determine \
whether it is a TRUE_POSITIVE or FALSE_POSITIVE.

Finding ID: finding-001
Content: "The system stores user email addresses for account recovery purposes."
Category: personal_data
Matched pattern: email

Respond with a ValidationResponse containing exactly one result for finding-001.\
"""


@pytest.mark.integration
@pytest.mark.batch
class TestAnthropicBatchIntegration:
    """End-to-end tests for Anthropic BatchLLMProvider methods."""

    async def test_submit_poll_and_retrieve_batch_results(
        self, require_anthropic_api_key: str
    ) -> None:
        """Full flow: submit batch, poll until completed, retrieve and verify results."""
        provider = AnthropicProvider(
            api_key=require_anthropic_api_key, model="claude-haiku-4-5"
        )

        schema: dict[str, JsonValue] = ValidationResponse.model_json_schema()
        requests = [
            BatchRequest(
                custom_id="integration-test-key-1",
                prompt=VALIDATION_PROMPT,
                model="claude-haiku-4-5",
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
        assert result.status == "completed", (
            f"Request failed with error: {result.error}"
        )
        assert result.response is not None

        # Verify the response can be parsed as our ValidationResponse
        parsed = ValidationResponse.model_validate(result.response)
        assert len(parsed.results) == 1
        assert parsed.results[0].finding_id == "finding-001"
        assert parsed.results[0].validation_result in (
            "TRUE_POSITIVE",
            "FALSE_POSITIVE",
        )

    async def test_cancel_batch(self, require_anthropic_api_key: str) -> None:
        """Submit a batch then immediately cancel it."""
        provider = AnthropicProvider(
            api_key=require_anthropic_api_key, model="claude-haiku-4-5"
        )

        schema: dict[str, JsonValue] = ValidationResponse.model_json_schema()
        requests = [
            BatchRequest(
                custom_id="integration-test-cancel-1",
                prompt=VALIDATION_PROMPT,
                model="claude-haiku-4-5",
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
