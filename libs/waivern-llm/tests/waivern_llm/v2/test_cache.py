"""Tests for LLMResponseCache.

Business behaviour: Provides cache key generation and CacheEntry management
for LLM response caching, delegating storage to an LLMCache implementation.
"""

from waivern_artifact_store.in_memory import AsyncInMemoryStore

from waivern_llm.v2.cache import CacheEntry, LLMResponseCache

# =============================================================================
# Key Generation
# =============================================================================


class TestLLMResponseCacheComputeKey:
    """Tests for the compute_key() method."""

    def test_compute_key_returns_deterministic_hash(self) -> None:
        store = AsyncInMemoryStore()
        cache = LLMResponseCache(store, "test-run")

        key1 = cache.compute_key("prompt", "model", "ResponseModel")
        key2 = cache.compute_key("prompt", "model", "ResponseModel")

        assert key1 == key2
        assert len(key1) == 64  # SHA256 produces 64 hex characters

    def test_compute_key_differs_for_different_prompts(self) -> None:
        store = AsyncInMemoryStore()
        cache = LLMResponseCache(store, "test-run")

        key1 = cache.compute_key("prompt A", "model", "ResponseModel")
        key2 = cache.compute_key("prompt B", "model", "ResponseModel")

        assert key1 != key2

    def test_compute_key_differs_for_different_models(self) -> None:
        store = AsyncInMemoryStore()
        cache = LLMResponseCache(store, "test-run")

        key1 = cache.compute_key("prompt", "claude-sonnet-4-5", "ResponseModel")
        key2 = cache.compute_key("prompt", "gpt-4o", "ResponseModel")

        assert key1 != key2

    def test_compute_key_differs_for_different_response_models(self) -> None:
        store = AsyncInMemoryStore()
        cache = LLMResponseCache(store, "test-run")

        key1 = cache.compute_key("prompt", "model", "ValidationResult")
        key2 = cache.compute_key("prompt", "model", "ClassificationResult")

        assert key1 != key2


# =============================================================================
# Cache Operations
# =============================================================================


class TestLLMResponseCacheGet:
    """Tests for the get() method."""

    async def test_get_returns_none_when_entry_not_found(self) -> None:
        store = AsyncInMemoryStore()
        cache = LLMResponseCache(store, "test-run")

        result = await cache.get("nonexistent-key")

        assert result is None


class TestLLMResponseCacheSet:
    """Tests for the set() method."""

    async def test_set_then_get_returns_cache_entry(self) -> None:
        store = AsyncInMemoryStore()
        cache = LLMResponseCache(store, "test-run")
        entry = CacheEntry(
            status="completed",
            response={"valid": True, "reason": "test"},
            batch_id=None,
            model_name="claude-sonnet-4-5",
            response_model_name="ValidationResult",
        )

        await cache.set("test-key", entry)

        retrieved = await cache.get("test-key")
        assert retrieved is not None
        assert retrieved.status == "completed"
        assert retrieved.response == {"valid": True, "reason": "test"}
        assert retrieved.model_name == "claude-sonnet-4-5"


class TestLLMResponseCacheDelete:
    """Tests for the delete() method."""

    async def test_delete_removes_entry(self) -> None:
        store = AsyncInMemoryStore()
        cache = LLMResponseCache(store, "test-run")
        entry = CacheEntry(
            status="completed",
            response={"data": "test"},
            batch_id=None,
            model_name="model",
            response_model_name="Response",
        )
        await cache.set("key1", entry)
        assert await cache.get("key1") is not None

        await cache.delete("key1")

        assert await cache.get("key1") is None


class TestLLMResponseCacheClear:
    """Tests for the clear() method."""

    async def test_clear_removes_all_entries(self) -> None:
        store = AsyncInMemoryStore()
        cache = LLMResponseCache(store, "test-run")
        for i in range(3):
            entry = CacheEntry(
                status="completed",
                response={"index": i},
                batch_id=None,
                model_name="model",
                response_model_name="Response",
            )
            await cache.set(f"key{i}", entry)

        await cache.clear()

        assert await cache.get("key0") is None
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
