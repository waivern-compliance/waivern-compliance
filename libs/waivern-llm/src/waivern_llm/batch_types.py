"""Batch mode data models for LLM provider batch APIs.

These types define the contract between the LLM service and batch-capable
providers (e.g., Anthropic Message Batches, OpenAI Batch API). They are
pure value objects — immutable after creation.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict
from waivern_core import JsonValue

type BatchStatusLiteral = Literal[
    "submitted", "in_progress", "completed", "failed", "expired", "cancelled"
]
"""Status values shared by BatchStatus and BatchJob."""


class BatchRequest(BaseModel):
    """A single prompt submission within a batch.

    The ``custom_id`` is the deterministic cache key (SHA256 of
    prompt|model|response_model), creating a direct mapping between
    batch results and cache entries.

    The ``response_schema`` carries the JSON schema for the expected
    response structure, enabling providers to enforce structured output
    in their batch API requests.
    """

    model_config = ConfigDict(frozen=True)

    custom_id: str
    prompt: str
    model: str
    response_schema: dict[str, JsonValue]


class BatchSubmission(BaseModel):
    """Confirmation returned by the provider after submitting a batch."""

    model_config = ConfigDict(frozen=True)

    batch_id: str
    request_count: int


class BatchStatus(BaseModel):
    """Polling response for a batch's processing status."""

    model_config = ConfigDict(frozen=True)

    batch_id: str
    status: BatchStatusLiteral
    completed_count: int
    failed_count: int
    total_count: int


class BatchResult(BaseModel):
    """Per-prompt result within a completed batch.

    The ``custom_id`` maps back to the cache key, allowing the poller
    to update the correct cache entry.
    """

    model_config = ConfigDict(frozen=True)

    custom_id: str
    status: Literal["completed", "failed"]
    response: dict[str, JsonValue] | None
    error: str | None
