"""Tests for CacheEntry.

Business behaviour: Provides cache key generation for LLM response caching.
The key ensures same inputs produce same key, and different inputs produce
different keys.
"""

from waivern_llm.cache import CacheEntry


class TestCacheEntryComputeKey:
    """Tests for the CacheEntry.compute_key() classmethod."""

    def test_compute_key_returns_deterministic_hash(self) -> None:
        key1 = CacheEntry.compute_key("prompt", "model", "ResponseModel")
        key2 = CacheEntry.compute_key("prompt", "model", "ResponseModel")

        assert key1 == key2
        assert len(key1) == 64  # SHA256 produces 64 hex characters

    def test_compute_key_differs_for_different_prompts(self) -> None:
        key1 = CacheEntry.compute_key("prompt A", "model", "ResponseModel")
        key2 = CacheEntry.compute_key("prompt B", "model", "ResponseModel")

        assert key1 != key2

    def test_compute_key_differs_for_different_models(self) -> None:
        key1 = CacheEntry.compute_key("prompt", "claude-sonnet-4-5", "ResponseModel")
        key2 = CacheEntry.compute_key("prompt", "gpt-4o", "ResponseModel")

        assert key1 != key2

    def test_compute_key_differs_for_different_response_models(self) -> None:
        key1 = CacheEntry.compute_key("prompt", "model", "ValidationResult")
        key2 = CacheEntry.compute_key("prompt", "model", "ClassificationResult")

        assert key1 != key2
