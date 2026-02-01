"""LLM Response Cache with key generation and entry management.

This module provides the LLMResponseCache wrapper that handles:
- Cache key generation (SHA256 of prompt + model + response_model)
- CacheEntry serialisation/deserialisation
- Delegation to LLMCache protocol implementations
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel
from waivern_core import JsonValue

if TYPE_CHECKING:
    from waivern_artifact_store.llm_cache import LLMCache


class CacheEntry(BaseModel):
    """LLM response cache entry.

    Tracks the status and response of an LLM request for caching
    and async batch resumption.
    """

    status: Literal["pending", "completed", "failed"]
    response: dict[str, JsonValue] | None
    batch_id: str | None  # For async batch mode
    model_name: str
    response_model_name: str


class LLMResponseCache:
    """LLM response cache with key generation and entry management.

    Wraps an LLMCache protocol implementation, providing:
    - Deterministic cache key generation (SHA256)
    - CacheEntry serialisation/deserialisation
    - Run-scoped cache operations
    """

    def __init__(self, store: LLMCache, run_id: str) -> None:
        """Initialise the cache.

        Args:
            store: LLMCache protocol implementation for storage.
            run_id: Run ID to scope cache entries.

        """
        self._store = store
        self._run_id = run_id

    def compute_key(self, prompt: str, model: str, response_model: str) -> str:
        """Compute cache key from prompt, model, and response model.

        Uses SHA256 hash of concatenated values to ensure:
        - Same inputs always produce same key (deterministic)
        - Different models/response_models cache separately

        Args:
            prompt: The LLM prompt text.
            model: Model name (e.g., 'claude-sonnet-4-5').
            response_model: Response model name (e.g., 'ValidationResult').

        Returns:
            64-character hex string (SHA256 hash).

        """
        combined = f"{prompt}|{model}|{response_model}"
        return hashlib.sha256(combined.encode()).hexdigest()

    async def get(self, key: str) -> CacheEntry | None:
        """Retrieve a cache entry by key.

        Args:
            key: Cache key (from compute_key).

        Returns:
            CacheEntry if found, None otherwise.

        """
        data = await self._store.cache_get(self._run_id, key)
        if data is None:
            return None
        return CacheEntry.model_validate(data)

    async def set(self, key: str, entry: CacheEntry) -> None:
        """Store a cache entry.

        Args:
            key: Cache key (from compute_key).
            entry: CacheEntry to store.

        """
        data = entry.model_dump()
        await self._store.cache_set(self._run_id, key, data)

    async def delete(self, key: str) -> None:
        """Delete a cache entry by key.

        Args:
            key: Cache key to delete.

        """
        await self._store.cache_delete(self._run_id, key)

    async def clear(self) -> None:
        """Delete all cache entries for this run.

        Called after LLMService.complete() returns successfully
        (Design Decision 9).
        """
        await self._store.cache_clear(self._run_id)
