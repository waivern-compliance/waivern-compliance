"""LLM Service interface.

This module defines the abstract LLMService interface that handles intelligent
batching internally, moving this responsibility from processors/analysers.

Key design principles:
- Processors decide what to group (domain logic)
- LLM Service decides how to batch (token-aware bin-packing)
- Unified cache handles both sync responses and async batch tracking
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from pydantic import BaseModel
from waivern_core import Finding

from waivern_llm.v2.types import BatchingMode, ItemGroup, PromptBuilder


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
    ) -> list[R]:
        """Process groups of findings and return structured responses.

        Orchestrates the complete flow:
        1. Plan batches using BatchPlanner based on batching_mode
        2. For each batch, build prompt and check cache
        3. Call LLM provider for cache misses
        4. Parse responses into response_model instances
        5. Handle skipped groups (log warning, exclude from results)

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
            List of response_model instances, one per batch processed.
            Skipped groups are excluded from results.

        Raises:
            LLMConnectionError: If LLM requests fail after retries.

        """
        ...
