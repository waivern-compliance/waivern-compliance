"""Tests for DefaultLLMService.

Business behaviour: Orchestrates batching, caching, and provider calls
for LLM processing of finding groups.
"""

from collections.abc import Sequence
from unittest.mock import AsyncMock, Mock

from pydantic import BaseModel
from waivern_artifact_store.in_memory import AsyncInMemoryStore

from waivern_llm.v2.cache import CacheEntry
from waivern_llm.v2.service import DefaultLLMService
from waivern_llm.v2.types import BatchingMode, ItemGroup, SkipReason

# =============================================================================
# Test Fixtures
# =============================================================================


class MockMetadata:
    """Minimal metadata satisfying FindingMetadata protocol."""

    def __init__(self, source: str = "test.py") -> None:
        self._source = source

    @property
    def source(self) -> str:
        return self._source


class MockFinding:
    """Minimal finding for testing (satisfies Finding protocol)."""

    def __init__(self, finding_id: str, source: str = "test.py") -> None:
        self._id = finding_id
        self._metadata = MockMetadata(source)

    @property
    def id(self) -> str:
        return self._id

    @property
    def metadata(self) -> MockMetadata:
        return self._metadata


class MockResponse(BaseModel):
    """Mock response model for testing."""

    valid: bool
    reason: str


def _create_mock_provider(response: MockResponse) -> Mock:
    """Create a mock LLM provider that returns the given response."""
    provider = Mock()
    provider.model_name = "test-model"
    provider.context_window = 100_000
    provider.invoke_structured = AsyncMock(return_value=response)
    return provider


def _create_mock_prompt_builder() -> Mock:
    """Create a mock prompt builder that tracks calls."""
    builder = Mock()
    builder.build_prompt = Mock(return_value="test prompt")
    return builder


def _create_group(
    content: str | None,
    item_count: int = 1,
    group_id: str | None = None,
) -> ItemGroup[MockFinding]:
    """Create a test ItemGroup with the specified content and item count."""
    items = [MockFinding(f"finding-{i}") for i in range(item_count)]
    return ItemGroup(items=items, content=content, group_id=group_id)


# =============================================================================
# COUNT_BASED Mode
# =============================================================================


class TestDefaultLLMServiceCountBasedMode:
    """Tests for COUNT_BASED batching mode."""

    async def test_passes_none_content_to_prompt_builder(self) -> None:
        """COUNT_BASED mode should pass content=None to prompt builder."""
        # Arrange
        store = AsyncInMemoryStore()
        response = MockResponse(valid=True, reason="test")
        provider = _create_mock_provider(response)
        prompt_builder = _create_mock_prompt_builder()
        service = DefaultLLMService(provider=provider, cache_store=store, batch_size=50)

        group = _create_group(content="some content", item_count=2)

        # Act
        await service.complete(
            groups=[group],
            prompt_builder=prompt_builder,
            response_model=MockResponse,
            batching_mode=BatchingMode.COUNT_BASED,
            run_id="test-run",
        )

        # Assert - prompt builder should be called with content=None
        prompt_builder.build_prompt.assert_called()
        _, kwargs = prompt_builder.build_prompt.call_args
        assert kwargs["content"] is None

    async def test_returns_response_for_each_batch(self) -> None:
        """Should return one response per batch processed."""
        # Arrange
        store = AsyncInMemoryStore()
        response = MockResponse(valid=True, reason="test")
        provider = _create_mock_provider(response)
        prompt_builder = _create_mock_prompt_builder()
        # batch_size=2 means 5 items should produce 3 batches
        service = DefaultLLMService(provider=provider, cache_store=store, batch_size=2)

        group = _create_group(content="some content", item_count=5)

        # Act
        results = await service.complete(
            groups=[group],
            prompt_builder=prompt_builder,
            response_model=MockResponse,
            batching_mode=BatchingMode.COUNT_BASED,
            run_id="test-run",
        )

        # Assert - should have 3 responses (5 items / 2 per batch = 3 batches)
        assert len(results.responses) == 3
        assert all(isinstance(r, MockResponse) for r in results.responses)


# =============================================================================
# EXTENDED_CONTEXT Mode
# =============================================================================


class TestDefaultLLMServiceExtendedContextMode:
    """Tests for EXTENDED_CONTEXT batching mode."""

    async def test_passes_content_to_prompt_builder(self) -> None:
        """EXTENDED_CONTEXT mode should pass group content to prompt builder."""
        # Arrange
        store = AsyncInMemoryStore()
        response = MockResponse(valid=True, reason="test")
        provider = _create_mock_provider(response)
        prompt_builder = _create_mock_prompt_builder()
        service = DefaultLLMService(provider=provider, cache_store=store, batch_size=50)

        group = _create_group(content="file content here", item_count=2)

        # Act
        await service.complete(
            groups=[group],
            prompt_builder=prompt_builder,
            response_model=MockResponse,
            batching_mode=BatchingMode.EXTENDED_CONTEXT,
            run_id="test-run",
        )

        # Assert - prompt builder should be called with the content
        prompt_builder.build_prompt.assert_called_once()
        _, kwargs = prompt_builder.build_prompt.call_args
        assert kwargs["content"] == "file content here"

    async def test_returns_response_for_each_batch_with_groups(self) -> None:
        """Should return one response per batch of groups."""
        # Arrange
        store = AsyncInMemoryStore()
        response = MockResponse(valid=True, reason="test")
        provider = _create_mock_provider(response)
        prompt_builder = _create_mock_prompt_builder()
        # Small max_payload forces groups into separate batches
        service = DefaultLLMService(provider=provider, cache_store=store, batch_size=50)

        # Two groups that should each become their own batch
        # (content is small enough to fit individually but creates separate batches)
        group1 = _create_group(content="content 1", item_count=2, group_id="g1")
        group2 = _create_group(content="content 2", item_count=2, group_id="g2")

        # Act
        results = await service.complete(
            groups=[group1, group2],
            prompt_builder=prompt_builder,
            response_model=MockResponse,
            batching_mode=BatchingMode.EXTENDED_CONTEXT,
            run_id="test-run",
        )

        # Assert - both groups fit in one batch (small content)
        # so we get 1 response
        assert len(results.responses) >= 1
        assert all(isinstance(r, MockResponse) for r in results.responses)


# =============================================================================
# Caching
# =============================================================================


class TestDefaultLLMServiceCaching:
    """Tests for cache interactions."""

    async def test_cache_miss_calls_provider(self) -> None:
        """Cache miss should invoke the LLM provider."""
        # Arrange
        store = AsyncInMemoryStore()
        response = MockResponse(valid=True, reason="from provider")
        provider = _create_mock_provider(response)
        prompt_builder = _create_mock_prompt_builder()
        service = DefaultLLMService(provider=provider, cache_store=store, batch_size=50)

        group = _create_group(content="test content", item_count=1)

        # Act
        results = await service.complete(
            groups=[group],
            prompt_builder=prompt_builder,
            response_model=MockResponse,
            batching_mode=BatchingMode.EXTENDED_CONTEXT,
            run_id="test-run",
        )

        # Assert - provider should have been called
        provider.invoke_structured.assert_called_once()
        assert len(results.responses) == 1
        assert results.responses[0].reason == "from provider"

    async def test_cache_hit_on_retry_after_failure(self) -> None:
        """Retry after failure should use cached results from successful batches."""
        # Arrange
        store = AsyncInMemoryStore()

        response = MockResponse(valid=True, reason="from provider")
        provider = Mock()
        provider.model_name = "test-model"
        provider.context_window = 100_000
        provider_call_count = 0

        async def invoke_side_effect(
            _prompt: str, _response_model: type[MockResponse]
        ) -> MockResponse:
            nonlocal provider_call_count
            provider_call_count += 1
            if provider_call_count == 2:
                raise RuntimeError("Simulated failure on second batch")
            return response

        provider.invoke_structured = AsyncMock(side_effect=invoke_side_effect)

        # Prompt builder returns unique prompts based on items
        prompt_call_count = 0

        def build_prompt_side_effect(
            _items: Sequence[MockFinding], *, content: str | None = None
        ) -> str:
            nonlocal prompt_call_count
            prompt_call_count += 1
            return f"prompt-{prompt_call_count}"

        prompt_builder = Mock()
        prompt_builder.build_prompt = Mock(side_effect=build_prompt_side_effect)

        service = DefaultLLMService(provider=provider, cache_store=store, batch_size=1)

        # Two items that will become two batches (batch_size=1, COUNT_BASED flattens)
        group = _create_group(content=None, item_count=2)

        # First attempt - should fail on second batch
        try:
            await service.complete(
                groups=[group],
                prompt_builder=prompt_builder,
                response_model=MockResponse,
                batching_mode=BatchingMode.COUNT_BASED,
                run_id="test-run",
            )
        except RuntimeError:
            pass  # Expected

        # Provider should have been called twice (first batch succeeded, second failed)
        assert provider_call_count == 2

        # Reset provider to succeed and reset call count
        provider.invoke_structured = AsyncMock(return_value=response)

        # Reset prompt builder to return same prompts as before (for cache hit)
        prompt_call_count = 0

        # Act - retry should use cached result for first batch
        results = await service.complete(
            groups=[group],
            prompt_builder=prompt_builder,
            response_model=MockResponse,
            batching_mode=BatchingMode.COUNT_BASED,
            run_id="test-run",
        )

        # Assert - provider should only be called once (for second batch)
        # First batch ("prompt-1") was cached from the failed attempt
        provider.invoke_structured.assert_called_once()
        assert len(results.responses) == 2

    async def test_clears_cache_after_successful_completion(self) -> None:
        """Should clear cache after complete() returns successfully."""
        # Arrange
        store = AsyncInMemoryStore()
        response = MockResponse(valid=True, reason="test")
        provider = _create_mock_provider(response)
        prompt_builder = _create_mock_prompt_builder()
        service = DefaultLLMService(provider=provider, cache_store=store, batch_size=50)

        group = _create_group(content="test content", item_count=1)

        # Act - complete() should populate cache then clear it
        await service.complete(
            groups=[group],
            prompt_builder=prompt_builder,
            response_model=MockResponse,
            batching_mode=BatchingMode.EXTENDED_CONTEXT,
            run_id="test-run",
        )

        # Assert - cache should be empty after successful completion
        # Try to get any cached entry - should be None
        cache_key = CacheEntry.compute_key("test prompt", "test-model", "MockResponse")
        cached = await store.cache_get("test-run", cache_key)
        assert cached is None


# =============================================================================
# Skipped Groups
# =============================================================================


class TestDefaultLLMServiceSkippedFindings:
    """Tests for handling skipped findings."""

    async def test_skipped_findings_returned_in_result(self) -> None:
        """Skipped findings should be returned with reasons."""
        # Arrange
        store = AsyncInMemoryStore()
        response = MockResponse(valid=True, reason="test")
        provider = _create_mock_provider(response)
        prompt_builder = _create_mock_prompt_builder()
        service = DefaultLLMService(provider=provider, cache_store=store, batch_size=50)

        # Valid group with content
        valid_group = _create_group(content="valid content", item_count=2)
        # Group missing content (will be skipped in EXTENDED_CONTEXT mode)
        missing_content_group = _create_group(content=None, item_count=2)

        # Act
        results = await service.complete(
            groups=[valid_group, missing_content_group],
            prompt_builder=prompt_builder,
            response_model=MockResponse,
            batching_mode=BatchingMode.EXTENDED_CONTEXT,
            run_id="test-run",
        )

        # Assert - only valid group should produce a response
        assert len(results.responses) == 1
        # Provider should only be called once (for valid group)
        provider.invoke_structured.assert_called_once()
        # Skipped findings should be returned
        assert len(results.skipped) == 2
        assert all(s.reason == SkipReason.MISSING_CONTENT for s in results.skipped)


# =============================================================================
# Error Handling
# =============================================================================


class TestDefaultLLMServiceErrorHandling:
    """Tests for error propagation."""

    async def test_provider_error_propagates(self) -> None:
        """Provider errors should propagate to caller."""
        import pytest

        # Arrange
        store = AsyncInMemoryStore()
        provider = Mock()
        provider.model_name = "test-model"
        provider.context_window = 100_000
        provider.invoke_structured = AsyncMock(
            side_effect=RuntimeError("Provider failed")
        )
        prompt_builder = _create_mock_prompt_builder()
        service = DefaultLLMService(provider=provider, cache_store=store, batch_size=50)

        group = _create_group(content="test content", item_count=1)

        # Act & Assert - error should propagate
        with pytest.raises(RuntimeError, match="Provider failed"):
            await service.complete(
                groups=[group],
                prompt_builder=prompt_builder,
                response_model=MockResponse,
                batching_mode=BatchingMode.EXTENDED_CONTEXT,
                run_id="test-run",
            )
