"""LLM Service interface and default implementation.

This module defines the abstract LLMService interface that handles intelligent
batching internally, moving this responsibility from processors/analysers.

Key design principles:
- Processors decide what to group (domain logic)
- LLM Service decides how to batch (token-aware bin-packing)
- Unified cache handles both sync responses and async batch tracking

Caching Architecture
--------------------

The cache uses a unified mechanism for both sync and async modes::

    SYNC MODE (current):
      prompt → SHA256(prompt|model|response_model) → cache miss → call LLM → cache(completed)

    ASYNC MODE (future Batch API):
      prompt → SHA256 → cache miss → submit batch → cache(pending, batch_id)
      ... later (poller) ...
      batch complete → cache(completed)

    RESUME (both modes):
      prompt → SHA256 → cache hit (completed) → return cached
      prompt → SHA256 → cache hit (pending) → skip (async in progress)
      prompt → SHA256 → cache miss → reprocess (data changed or new)

Cache is scoped by ``run_id`` to isolate concurrent executions. The cache key
includes prompt, model name, and response model name so that:
- Same prompt with different models caches separately
- Same prompt with different response schemas caches separately

Cache entries are **cleared after successful completion** - the cache is
temporary working storage for resumability, not permanent state. Artifacts
(the actual findings and results) are the permanent record.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast, override

from pydantic import BaseModel
from waivern_core import Finding

from waivern_llm.batch_job import BatchJob
from waivern_llm.batch_planner import BatchPlanner, PlannedBatch
from waivern_llm.batch_types import BatchRequest
from waivern_llm.cache import CacheEntry
from waivern_llm.errors import PendingBatchError
from waivern_llm.providers.protocol import BatchLLMProvider, LLMProvider
from waivern_llm.token_estimation import calculate_max_payload_tokens
from waivern_llm.types import (
    BatchingMode,
    ItemGroup,
    LLMCompletionResult,
    PromptBuilder,
    SkippedFinding,
)

if TYPE_CHECKING:
    from waivern_artifact_store.base import ArtifactStore
    from waivern_artifact_store.llm_cache import LLMCache


class LLMService(ABC):
    """Abstract base class for LLM service implementations.

    The LLM service handles intelligent batching and caching, allowing processors
    to focus on domain logic (grouping, prompt building) rather than batching
    mechanics.

    Processors call `complete()` with groups of findings and a prompt builder.
    The service:
    1. Plans batches based on the batching mode and model context window
    2. Builds prompts for each batch using the provided prompt builder
    3. Checks cache for existing responses
    4. Calls the LLM provider for cache misses
    5. Caches responses and returns parsed results

    Type Parameters:
        T: Finding type (bound to Finding protocol)
        R: Response model type (bound to BaseModel)

    """

    @abstractmethod
    async def complete[T: Finding, R: BaseModel](
        self,
        groups: Sequence[ItemGroup[T]],
        *,
        prompt_builder: PromptBuilder[T],
        response_model: type[R],
        batching_mode: BatchingMode = BatchingMode.COUNT_BASED,
        run_id: str,
    ) -> LLMCompletionResult[T, R]:
        """Process groups of findings and return structured responses.

        Orchestrates the complete flow:
        1. Plan batches using BatchPlanner based on batching_mode
        2. For each batch, build prompt and check cache
        3. Call LLM provider for cache misses
        4. Parse responses into response_model instances
        5. Collect skipped findings and return them to caller

        Args:
            groups: Groups of findings to process. Each group may have
                optional shared content for extended-context mode.
            prompt_builder: Processor-provided builder that creates prompts
                from items and optional content.
            response_model: Pydantic model class defining expected output
                structure from the LLM.
            batching_mode: How to batch items. COUNT_BASED flattens all items
                and splits by count. EXTENDED_CONTEXT keeps groups intact
                and bin-packs by tokens. Defaults to COUNT_BASED.
            run_id: Unique identifier for the current run, used for cache scoping.

        Returns:
            LLMCompletionResult containing:
            - responses: List of response_model instances, one per batch
            - skipped: List of individual findings that could not be processed

        Raises:
            LLMConnectionError: If LLM requests fail after retries.

        """
        ...


class DefaultLLMService(LLMService):
    """Default LLM service implementation.

    Orchestrates batching, caching, and provider calls with two code paths:

    **Sync path** (default):
    1. Plan batches → build prompts → check cache → call provider → cache → return

    **Batch path** (``batch_mode=True`` and provider implements ``BatchLLMProvider``):
    1. Plan batches → build prompts → check cache
    2. Collect cache misses → submit batch → write pending cache entries → save BatchJob
    3. Raise ``PendingBatchError`` if any entries still pending
    4. On resume (all completed) → return results normally
    """

    def __init__(
        self,
        provider: LLMProvider,
        store: ArtifactStore,
        batch_size: int = 50,
        *,
        batch_mode: bool = False,
        provider_name: str = "",
    ) -> None:
        """Initialise the service.

        Args:
            provider: LLM provider for making structured calls.
            store: Artifact store for response caching and batch job persistence.
            batch_size: Maximum items per batch in COUNT_BASED mode.
            batch_mode: Use batch API for async processing (lower cost).
            provider_name: Provider name for batch job metadata (e.g. "anthropic").

        """
        self._provider = provider
        self._store = store
        # ArtifactStore implementations also satisfy the LLMCache protocol;
        # cast once here so cache operations are type-safe throughout.
        self._cache: LLMCache = cast("LLMCache", store)
        self._batch_size = batch_size
        self._batch_mode = batch_mode
        self._provider_name = provider_name

    def _use_batch_path(self) -> bool:
        """Check whether to use the batch API path."""
        return self._batch_mode and isinstance(self._provider, BatchLLMProvider)

    @override
    async def complete[T: Finding, R: BaseModel](
        self,
        groups: Sequence[ItemGroup[T]],
        *,
        prompt_builder: PromptBuilder[T],
        response_model: type[R],
        batching_mode: BatchingMode = BatchingMode.COUNT_BASED,
        run_id: str,
    ) -> LLMCompletionResult[T, R]:
        """Process groups of findings and return structured responses.

        Orchestrates the complete flow:
        1. Plan batches using BatchPlanner based on batching_mode
        2. For each batch, build prompt and check cache
        3. Sync path: call provider for cache misses
        4. Batch path: submit misses to batch API, raise PendingBatchError
        5. On resume with all completed: return results normally
        """
        max_payload = calculate_max_payload_tokens(self._provider.context_window)
        planner = BatchPlanner(
            max_payload_tokens=max_payload,
            batch_size=self._batch_size,
        )

        plan = planner.plan(groups, batching_mode)

        if self._use_batch_path():
            return await self._complete_batch(
                plan.batches, prompt_builder, response_model, run_id, plan.skipped
            )

        return await self._complete_sync(
            plan.batches, prompt_builder, response_model, run_id, plan.skipped
        )

    def _build_prompt_and_key[T: Finding](
        self,
        batch: PlannedBatch[T],
        prompt_builder: PromptBuilder[T],
        response_model_name: str,
    ) -> tuple[str, str]:
        """Build prompt from batch groups and compute its cache key.

        Args:
            batch: Planned batch containing item groups.
            prompt_builder: Domain-specific prompt builder.
            response_model_name: Name of the response model (for cache key).

        Returns:
            Tuple of (prompt, cache_key).

        """
        all_items: list[T] = []
        content: str | None = None
        for group in batch.groups:
            all_items.extend(group.items)
            if group.content is not None:
                content = group.content

        prompt = prompt_builder.build_prompt(all_items, content=content)

        cache_key = CacheEntry.compute_key(
            prompt=prompt,
            model=self._provider.model_name,
            response_model=response_model_name,
        )
        return prompt, cache_key

    async def _get_cached_entry(
        self,
        run_id: str,
        cache_key: str,
    ) -> CacheEntry | None:
        """Load a cache entry if one exists.

        Args:
            run_id: Current run identifier.
            cache_key: Cache key to look up.

        Returns:
            Parsed CacheEntry, or None if no entry exists.

        """
        cached_data = await self._cache.cache_get(run_id, cache_key)
        if cached_data is not None:
            return CacheEntry.model_validate(cached_data)
        return None

    async def _complete_sync[T: Finding, R: BaseModel](
        self,
        batches: Sequence[PlannedBatch[T]],
        prompt_builder: PromptBuilder[T],
        response_model: type[R],
        run_id: str,
        skipped: list[SkippedFinding[T]],
    ) -> LLMCompletionResult[T, R]:
        """Execute the synchronous code path — call provider for each cache miss."""
        responses: list[R] = []
        for batch in batches:
            prompt, cache_key = self._build_prompt_and_key(
                batch, prompt_builder, response_model.__name__
            )

            cached = await self._get_cached_entry(run_id, cache_key)
            if cached is not None and cached.status == "completed" and cached.response:
                responses.append(response_model.model_validate(cached.response))
                continue

            response = await self._provider.invoke_structured(prompt, response_model)

            entry = CacheEntry(
                status="completed",
                response=response.model_dump(),
                batch_id=None,
                model_name=self._provider.model_name,
                response_model_name=response_model.__name__,
            )
            await self._cache.cache_set(run_id, cache_key, entry.model_dump())
            responses.append(response)

        await self._cache.cache_clear(run_id)
        return LLMCompletionResult(responses=responses, skipped=skipped)

    async def _complete_batch[T: Finding, R: BaseModel](
        self,
        batches: Sequence[PlannedBatch[T]],
        prompt_builder: PromptBuilder[T],
        response_model: type[R],
        run_id: str,
        skipped: list[SkippedFinding[T]],
    ) -> LLMCompletionResult[T, R]:
        """Execute the batch API code path.

        Flow:
        1. For each planned batch, build prompt and check cache
        2. Collect cache misses as BatchRequests for submission
        3. Submit misses to provider, write pending cache entries, save BatchJob
        4. If any pending entries remain, raise PendingBatchError
        5. If all completed (resume path), clear cache and return results
        """
        responses: list[R] = []
        pending_batch_ids: list[str] = []
        requests_to_submit: list[BatchRequest] = []
        cache_keys_for_submission: list[str] = []

        for batch in batches:
            prompt, cache_key = self._build_prompt_and_key(
                batch, prompt_builder, response_model.__name__
            )

            cached = await self._get_cached_entry(run_id, cache_key)
            if cached is not None:
                if cached.status == "completed" and cached.response:
                    responses.append(response_model.model_validate(cached.response))
                    continue
                if cached.status == "pending" and cached.batch_id:
                    pending_batch_ids.append(cached.batch_id)
                    continue

            # Cache miss — collect for batch submission
            requests_to_submit.append(
                BatchRequest(
                    custom_id=cache_key,
                    prompt=prompt,
                    model=self._provider.model_name,
                )
            )
            cache_keys_for_submission.append(cache_key)

        # Submit collected misses
        if requests_to_submit:
            provider = cast("BatchLLMProvider", self._provider)
            submission = await provider.submit_batch(requests_to_submit)

            # Write pending cache entries
            for key in cache_keys_for_submission:
                entry = CacheEntry(
                    status="pending",
                    response=None,
                    batch_id=submission.batch_id,
                    model_name=self._provider.model_name,
                    response_model_name=response_model.__name__,
                )
                await self._cache.cache_set(run_id, key, entry.model_dump())

            # Save BatchJob for tracking
            job = BatchJob(
                batch_id=submission.batch_id,
                run_id=run_id,
                provider=self._provider_name,
                model=self._provider.model_name,
                status="submitted",
                cache_keys=cache_keys_for_submission,
                request_count=submission.request_count,
                submitted_at=datetime.now(UTC),
                completed_at=None,
            )
            await job.save(self._store)

            pending_batch_ids.append(submission.batch_id)

        # If any pending entries remain, raise PendingBatchError
        # (do NOT clear cache — entries needed for resume)
        if pending_batch_ids:
            raise PendingBatchError(run_id=run_id, batch_ids=pending_batch_ids)

        # All completed (resume path) — clear cache and return
        await self._cache.cache_clear(run_id)
        return LLMCompletionResult(responses=responses, skipped=skipped)
