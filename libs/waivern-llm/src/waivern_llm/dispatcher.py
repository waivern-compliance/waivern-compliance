"""LLM Dispatcher for cross-processor execution consolidation.

Consolidates LLM execution across multiple dispatch requests. Each request
is planned independently (batching, prompt building, cache checking), but
execution is consolidated: sync mode uses ``asyncio.gather()`` for all
cache misses; batch mode uses a single ``submit_batch()`` call.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel

from waivern_llm.batch_job import BatchJob
from waivern_llm.batch_planner import BatchPlanner
from waivern_llm.batch_types import BatchRequest
from waivern_llm.cache import CacheEntry
from waivern_llm.errors import LLMServiceError, PendingBatchError
from waivern_llm.providers.protocol import BatchLLMProvider, LLMProvider
from waivern_llm.token_estimation import calculate_max_payload_tokens
from waivern_llm.types import (
    LLMDispatchResult,
    LLMRequest,
    SkippedFinding,
    SkipReason,
)

if TYPE_CHECKING:
    from waivern_artifact_store.base import ArtifactStore
    from waivern_artifact_store.llm_cache import LLMCache
    from waivern_core import Finding, JsonValue


class LLMDispatcher:
    """Dispatches LLM requests with cross-request execution consolidation.

    Implements ``RequestDispatcher[LLMRequest, LLMDispatchResult]``.

    Dispatch flow:
    1. Phase A — per-request planning (or cache key lookup on resume)
    2. Phase B — consolidated execution of all cache misses
    3. Phase C — build results per request
    """

    def __init__(
        self,
        provider: LLMProvider,
        store: ArtifactStore,
        *,
        batch_mode: bool = False,
    ) -> None:
        """Initialise the dispatcher.

        Args:
            provider: LLM provider for structured calls.
            store: Artifact store for caching and batch job persistence.
            batch_mode: Use batch API for async processing.

        """
        self._provider = provider
        self._store = store
        self._cache: LLMCache = cast("LLMCache", store)
        self._batch_mode = batch_mode

    @property
    def request_type(self) -> type[LLMRequest[Any]]:
        """The concrete request type this dispatcher handles."""
        return LLMRequest

    def _use_batch_path(self) -> bool:
        return self._batch_mode and isinstance(self._provider, BatchLLMProvider)

    async def dispatch(
        self, requests: Sequence[LLMRequest[Any]]
    ) -> Sequence[LLMDispatchResult]:
        """Dispatch LLM requests with consolidated execution.

        Orchestrates the complete dispatch flow:
        1. Per-request: plan batches, build prompts, check cache
           (or use stored cache keys on resume)
        2. Consolidated: execute all cache misses together
        3. Per-request: build results with responses and skipped findings
        """
        if not requests:
            return []

        run_ids = {r.run_id for r in requests}
        if len(run_ids) > 1:
            raise ValueError(
                f"All requests must share the same run_id, got: {sorted(run_ids)}"
            )

        run_id = requests[0].run_id

        # Per-request state accumulators
        request_responses: dict[str, list[dict[str, JsonValue]]] = {}
        request_skipped: dict[str, list[SkippedFinding[Finding]]] = {}
        cache_misses: list[_CacheMiss] = []
        pending_batch_ids: list[str] = []

        # Phase A — per-request planning or resume cache lookup
        for request in requests:
            request_responses[request.request_id] = []
            request_skipped[request.request_id] = []

            if request.built_cache_keys is not None:
                # Resume path — use stored cache keys directly
                await self._collect_from_cache_keys(
                    request, request_responses, pending_batch_ids
                )
            else:
                # First run — plan, build prompts, check cache
                await self._plan_and_check_cache(
                    request,
                    request_responses,
                    request_skipped,
                    cache_misses,
                    pending_batch_ids,
                )

        # Phase B — consolidated execution
        if cache_misses:
            if self._use_batch_path():
                await self._execute_batch(run_id, cache_misses, pending_batch_ids)
            else:
                await self._execute_sync(
                    run_id, cache_misses, request_responses, request_skipped
                )

        # Batch mode: raise if any pending
        if self._use_batch_path() and pending_batch_ids:
            raise PendingBatchError(run_id=run_id, batch_ids=pending_batch_ids)

        # Phase C — build results
        await self._cache.cache_clear(run_id)

        return [
            LLMDispatchResult(
                request_id=request.request_id,
                model_name=self._provider.model_name,
                responses=request_responses[request.request_id],
                skipped=request_skipped.get(request.request_id, []),
            )
            for request in requests
        ]

    async def _plan_and_check_cache(
        self,
        request: LLMRequest[Any],
        request_responses: dict[str, list[dict[str, JsonValue]]],
        request_skipped: dict[str, list[SkippedFinding[Finding]]],
        cache_misses: list[_CacheMiss],
        pending_batch_ids: list[str],
    ) -> None:
        """Phase A (first run): plan batches, build prompts, check cache."""
        max_payload = calculate_max_payload_tokens(self._provider.context_window)
        planner = BatchPlanner(max_payload_tokens=max_payload)
        plan = planner.plan(request.groups, request.batching_mode)

        request_skipped[request.request_id].extend(plan.skipped)

        cache_keys: list[str] = []
        for batch in plan.batches:
            prompt = request.prompt_builder.build_prompt(batch.groups)
            cache_key = CacheEntry.compute_key(
                prompt=prompt,
                model=self._provider.model_name,
                response_model=request.response_model.__name__,
            )
            cache_keys.append(cache_key)

            cached = await self._get_cached_entry(request.run_id, cache_key)
            if cached is not None:
                if cached.status == "completed" and cached.response:
                    request_responses[request.request_id].append(cached.response)
                    continue
                if cached.status == "pending" and cached.batch_id:
                    pending_batch_ids.append(cached.batch_id)
                    continue

            # Collect findings from this batch so we can produce
            # SkippedFinding(reason=BATCH_ERROR) if invoke_structured() fails.
            batch_findings: list[Finding] = [
                item for group in batch.groups for item in group.items
            ]
            cache_misses.append(
                _CacheMiss(
                    prompt=prompt,
                    cache_key=cache_key,
                    response_model=request.response_model,
                    request_id=request.request_id,
                    run_id=request.run_id,
                    findings=batch_findings,
                )
            )

        request.built_cache_keys = cache_keys

    async def _collect_from_cache_keys(
        self,
        request: LLMRequest[Any],
        request_responses: dict[str, list[dict[str, JsonValue]]],
        pending_batch_ids: list[str],
    ) -> None:
        """Phase A (resume): look up cache using stored keys."""
        if request.built_cache_keys is None:
            return
        for cache_key in request.built_cache_keys:
            cached = await self._get_cached_entry(request.run_id, cache_key)
            if cached is not None:
                if cached.status == "completed" and cached.response:
                    request_responses[request.request_id].append(cached.response)
                    continue
                if cached.status == "pending" and cached.batch_id:
                    pending_batch_ids.append(cached.batch_id)
                    continue

            raise LLMServiceError(
                f"Cache entry missing for key '{cache_key}' on resume. "
                f"Cannot re-execute without prompt_builder and response_model."
            )

    async def _get_cached_entry(self, run_id: str, cache_key: str) -> CacheEntry | None:
        cached_data = await self._cache.cache_get(run_id, cache_key)
        if cached_data is not None:
            return CacheEntry.model_validate(cached_data)
        return None

    async def _execute_sync(
        self,
        run_id: str,
        cache_misses: list[_CacheMiss],
        request_responses: dict[str, list[dict[str, JsonValue]]],
        request_skipped: dict[str, list[SkippedFinding[Finding]]],
    ) -> None:
        """Phase B (sync): execute all cache misses concurrently."""

        async def _invoke(miss: _CacheMiss) -> tuple[_CacheMiss, BaseModel]:
            response = await self._provider.invoke_structured(
                miss.prompt, miss.response_model
            )
            return miss, response

        results = await asyncio.gather(
            *[_invoke(miss) for miss in cache_misses],
            return_exceptions=True,
        )

        for i, result in enumerate(results):
            miss = cache_misses[i]
            if isinstance(result, BaseException):
                request_skipped[miss.request_id].extend(
                    SkippedFinding(finding=f, reason=SkipReason.BATCH_ERROR)
                    for f in miss.findings
                )
                continue

            _, response = result
            response_dict: dict[str, JsonValue] = response.model_dump()

            entry = CacheEntry(
                status="completed",
                response=response_dict,
                batch_id=None,
            )
            await self._cache.cache_set(run_id, miss.cache_key, entry.model_dump())
            request_responses[miss.request_id].append(response_dict)

    async def _execute_batch(
        self,
        run_id: str,
        cache_misses: list[_CacheMiss],
        pending_batch_ids: list[str],
    ) -> None:
        """Phase B (batch): submit all cache misses in a single batch call."""
        provider = cast("BatchLLMProvider", self._provider)

        batch_requests = [
            BatchRequest(
                custom_id=miss.cache_key,
                prompt=miss.prompt,
                model=self._provider.model_name,
                response_schema=miss.response_model.model_json_schema(),
            )
            for miss in cache_misses
        ]

        submission = await provider.submit_batch(batch_requests)

        for miss in cache_misses:
            entry = CacheEntry(
                status="pending",
                response=None,
                batch_id=submission.batch_id,
            )
            await self._cache.cache_set(run_id, miss.cache_key, entry.model_dump())

        job = BatchJob(
            batch_id=submission.batch_id,
            run_id=run_id,
            model=self._provider.model_name,
            status="submitted",
            cache_keys=[miss.cache_key for miss in cache_misses],
            request_count=submission.request_count,
            submitted_at=datetime.now(UTC),
            completed_at=None,
        )
        await job.save(self._store)

        pending_batch_ids.append(submission.batch_id)


class _CacheMiss:
    """Internal: tracks a cache miss pending execution."""

    __slots__ = (
        "prompt",
        "cache_key",
        "response_model",
        "request_id",
        "run_id",
        "findings",
    )

    def __init__(  # noqa: PLR0913 - data carrier
        self,
        prompt: str,
        cache_key: str,
        response_model: type[BaseModel],
        request_id: str,
        run_id: str,
        findings: list[Finding],
    ) -> None:
        self.prompt = prompt
        self.cache_key = cache_key
        self.response_model = response_model
        self.request_id = request_id
        self.run_id = run_id
        self.findings = findings
