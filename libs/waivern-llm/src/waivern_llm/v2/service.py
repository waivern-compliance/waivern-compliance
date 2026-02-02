"""LLM Service interface and default implementation.

This module defines the abstract LLMService interface that handles intelligent
batching internally, moving this responsibility from processors/analysers.

Key design principles:
- Processors decide what to group (domain logic)
- LLM Service decides how to batch (token-aware bin-packing)
- Unified cache handles both sync responses and async batch tracking
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import override

from pydantic import BaseModel
from waivern_core import Finding

from waivern_llm.v2.batch_planner import BatchPlanner
from waivern_llm.v2.cache import CacheEntry, LLMResponseCache
from waivern_llm.v2.providers.protocol import LLMProvider
from waivern_llm.v2.token_estimation import calculate_max_payload_tokens
from waivern_llm.v2.types import (
    BatchingMode,
    ItemGroup,
    LLMCompletionResult,
    PromptBuilder,
)


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

    Orchestrates batching, caching, and provider calls:
    1. Plan batches using BatchPlanner based on batching_mode
    2. For each batch, build prompt and check cache
    3. Call LLM provider for cache misses
    4. Cache responses and return parsed results
    5. Clean up cache after successful completion
    """

    def __init__(
        self,
        provider: LLMProvider,
        cache: LLMResponseCache,
        batch_size: int = 50,
    ) -> None:
        """Initialise the service.

        Args:
            provider: LLM provider for making structured calls.
            cache: Response cache for deduplication.
            batch_size: Maximum items per batch in COUNT_BASED mode.

        """
        self._provider = provider
        self._cache = cache
        self._batch_size = batch_size

    @override
    async def complete[T: Finding, R: BaseModel](
        self,
        groups: Sequence[ItemGroup[T]],
        *,
        prompt_builder: PromptBuilder[T],
        response_model: type[R],
        batching_mode: BatchingMode = BatchingMode.COUNT_BASED,
    ) -> LLMCompletionResult[T, R]:
        """Process groups of findings and return structured responses."""
        # Create batch planner with provider's context window
        max_payload = calculate_max_payload_tokens(self._provider.context_window)
        planner = BatchPlanner(
            max_payload_tokens=max_payload,
            batch_size=self._batch_size,
        )

        # Plan batches
        plan = planner.plan(groups, batching_mode)

        # Process each batch
        responses: list[R] = []
        for batch in plan.batches:
            # Flatten items and get content from groups
            all_items: list[T] = []
            content: str | None = None
            for group in batch.groups:
                all_items.extend(group.items)
                if group.content is not None:
                    content = group.content

            # Build prompt
            prompt = prompt_builder.build_prompt(all_items, content=content)

            # Check cache first
            cache_key = self._cache.compute_key(
                prompt=prompt,
                model=self._provider.model_name,
                response_model=response_model.__name__,
            )
            cached = await self._cache.get(cache_key)

            if cached is not None and cached.status == "completed" and cached.response:
                # Cache hit - parse and use cached response
                response = response_model.model_validate(cached.response)
            else:
                # Cache miss - call provider
                response = await self._provider.invoke_structured(
                    prompt, response_model
                )

                # Store in cache
                entry = CacheEntry(
                    status="completed",
                    response=response.model_dump(),
                    batch_id=None,
                    model_name=self._provider.model_name,
                    response_model_name=response_model.__name__,
                )
                await self._cache.set(cache_key, entry)

            responses.append(response)

        # Clean up cache after successful completion (Design Decision #9)
        await self._cache.clear()

        return LLMCompletionResult(responses=responses, skipped=plan.skipped)
