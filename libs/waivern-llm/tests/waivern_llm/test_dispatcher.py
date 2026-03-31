"""Tests for LLMDispatcher.

Business behaviour: Consolidates LLM execution across multiple dispatch
requests — planning per-request, executing consolidated, routing results
back by request_id.
"""

from typing import cast
from unittest.mock import AsyncMock, Mock

from pydantic import BaseModel
from waivern_artifact_store.in_memory import AsyncInMemoryStore

from waivern_llm.dispatcher import LLMDispatcher
from waivern_llm.types import BatchingMode, ItemGroup, LLMRequest

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


class MockClassification(BaseModel):
    """Second mock response model for multi-request tests."""

    category: str


def _create_mock_provider(response: MockResponse) -> Mock:
    """Create a mock LLM provider that returns the given response."""
    provider = Mock()
    provider.model_name = "test-model"
    provider.context_window = 100_000
    provider.invoke_structured = AsyncMock(return_value=response)
    return provider


def _create_mock_prompt_builder() -> Mock:
    """Create a mock prompt builder that returns a fixed prompt."""
    builder = Mock()
    builder.build_prompt = Mock(return_value="test prompt")
    return builder


def _create_unique_prompt_builder() -> Mock:
    """Create a prompt builder that returns unique prompts per call."""
    call_count = 0

    def build_prompt_side_effect(
        _groups: list[ItemGroup[MockFinding]],
    ) -> str:
        nonlocal call_count
        call_count += 1
        return f"prompt-{call_count}"

    builder = Mock()
    builder.build_prompt = Mock(side_effect=build_prompt_side_effect)
    return builder


def _create_request(
    item_count: int = 1,
    content: str | None = None,
    batching_mode: BatchingMode = BatchingMode.COUNT_BASED,
    run_id: str = "run-1",
) -> LLMRequest[MockFinding]:
    """Create an LLMRequest with sensible defaults for testing."""
    items = [MockFinding(f"finding-{i}") for i in range(item_count)]
    group: ItemGroup[MockFinding] = ItemGroup(items=items, content=content)
    return LLMRequest(
        groups=[group],
        prompt_builder=_create_mock_prompt_builder(),
        response_model=MockResponse,
        batching_mode=batching_mode,
        run_id=run_id,
    )


# =============================================================================
# Sync Mode — First Run
# =============================================================================


class TestLLMDispatcherSyncFirstRun:
    """Tests for sync mode first-run dispatch."""

    async def test_single_request_returns_result_with_correct_metadata(self) -> None:
        """Single request → result has matching request_id, model_name, name, and response_model_name."""
        store = AsyncInMemoryStore()
        response = MockResponse(valid=True, reason="ok")
        provider = _create_mock_provider(response)

        dispatcher = LLMDispatcher(provider=provider, store=store)
        request = _create_request()

        results = await dispatcher.dispatch([request])

        assert len(results) == 1
        assert results[0].request_id == request.request_id
        assert results[0].model_name == "test-model"
        assert results[0].name == ""
        assert results[0].response_model_name == "MockResponse"

    async def test_cache_miss_calls_provider_and_returns_raw_response(self) -> None:
        """Cache miss → invoke_structured() called, response returned as raw dict."""
        store = AsyncInMemoryStore()
        response = MockResponse(valid=True, reason="from provider")
        provider = _create_mock_provider(response)

        dispatcher = LLMDispatcher(provider=provider, store=store)
        request = _create_request()

        results = await dispatcher.dispatch([request])

        provider.invoke_structured.assert_called_once()
        assert len(results[0].responses) == 1
        assert results[0].responses[0] == {"valid": True, "reason": "from provider"}

    async def test_cache_hit_skips_provider_call(self) -> None:
        """Pre-populated cache → provider NOT called, cached response returned."""
        store = AsyncInMemoryStore()
        provider = _create_mock_provider(MockResponse(valid=True, reason="unused"))

        # Pre-populate cache with a completed entry
        from waivern_llm.cache import CacheEntry

        cache_key = CacheEntry.compute_key("test prompt", "test-model", "MockResponse")
        entry = CacheEntry(
            status="completed",
            response={"valid": False, "reason": "from cache"},
            batch_id=None,
        )
        await store.cache_set("run-1", cache_key, entry.model_dump())

        dispatcher = LLMDispatcher(provider=provider, store=store)
        request = _create_request(run_id="run-1")

        results = await dispatcher.dispatch([request])

        provider.invoke_structured.assert_not_called()
        assert results[0].responses[0] == {"valid": False, "reason": "from cache"}

    async def test_mixed_cache_hits_and_misses(self) -> None:
        """Some cached, some not → provider called only for misses."""
        store = AsyncInMemoryStore()
        response = MockResponse(valid=True, reason="from provider")
        provider = _create_mock_provider(response)
        # 1 item per batch
        provider.context_window = 4385

        # Pre-populate cache for prompt-1 (completed)
        from waivern_llm.cache import CacheEntry

        key_1 = CacheEntry.compute_key("prompt-1", "test-model", "MockResponse")
        entry_1 = CacheEntry(
            status="completed",
            response={"valid": False, "reason": "cached"},
            batch_id=None,
        )
        await store.cache_set("run-1", key_1, entry_1.model_dump())

        dispatcher = LLMDispatcher(provider=provider, store=store)
        request = _create_request(item_count=2, run_id="run-1")
        request.prompt_builder = _create_unique_prompt_builder()

        results = await dispatcher.dispatch([request])

        # Provider called once (for prompt-2 miss), not twice
        provider.invoke_structured.assert_called_once()
        assert len(results[0].responses) == 2

    async def test_multiple_requests_consolidated_concurrently(self) -> None:
        """Two requests with misses → all misses executed concurrently, results routed correctly."""
        store = AsyncInMemoryStore()

        # Provider returns different responses based on prompt
        async def invoke_side_effect(
            prompt: str, _response_model: type[MockResponse]
        ) -> MockResponse:
            if "request-A" in prompt:
                return MockResponse(valid=True, reason="result-A")
            return MockResponse(valid=False, reason="result-B")

        provider = Mock()
        provider.model_name = "test-model"
        provider.context_window = 100_000
        provider.invoke_structured = AsyncMock(side_effect=invoke_side_effect)

        dispatcher = LLMDispatcher(provider=provider, store=store)

        # Two requests with distinct prompts
        builder_a = Mock()
        builder_a.build_prompt = Mock(return_value="request-A prompt")
        request_a = LLMRequest(
            groups=[ItemGroup(items=[MockFinding("f1")])],
            prompt_builder=builder_a,
            response_model=MockResponse,
            batching_mode=BatchingMode.COUNT_BASED,
            run_id="run-1",
        )

        builder_b = Mock()
        builder_b.build_prompt = Mock(return_value="request-B prompt")
        request_b = LLMRequest(
            groups=[ItemGroup(items=[MockFinding("f2")])],
            prompt_builder=builder_b,
            response_model=MockResponse,
            batching_mode=BatchingMode.COUNT_BASED,
            run_id="run-1",
        )

        results = await dispatcher.dispatch([request_a, request_b])

        # Both requests should have results routed correctly
        assert len(results) == 2
        result_a = next(r for r in results if r.request_id == request_a.request_id)
        result_b = next(r for r in results if r.request_id == request_b.request_id)
        assert result_a.responses[0]["reason"] == "result-A"
        assert result_b.responses[0]["reason"] == "result-B"

        # Provider called twice (one per miss, consolidated via gather)
        assert provider.invoke_structured.call_count == 2

    async def test_multiple_requests_carry_correct_response_model_names(self) -> None:
        """Two requests with different response models → each result has the correct response_model_name."""
        store = AsyncInMemoryStore()

        async def invoke_side_effect(
            prompt: str, response_model: type[BaseModel]
        ) -> BaseModel:
            if response_model is MockClassification:
                return MockClassification(category="personal-data")
            return MockResponse(valid=True, reason="ok")

        provider = Mock()
        provider.model_name = "test-model"
        provider.context_window = 100_000
        provider.invoke_structured = AsyncMock(side_effect=invoke_side_effect)

        dispatcher = LLMDispatcher(provider=provider, store=store)

        builder_a = Mock()
        builder_a.build_prompt = Mock(return_value="prompt-A")
        request_a = LLMRequest(
            name="assessment",
            groups=[ItemGroup(items=[MockFinding("f1")])],
            prompt_builder=builder_a,
            response_model=MockResponse,
            batching_mode=BatchingMode.COUNT_BASED,
            run_id="run-1",
        )

        builder_b = Mock()
        builder_b.build_prompt = Mock(return_value="prompt-B")
        request_b = LLMRequest(
            name="classification",
            groups=[ItemGroup(items=[MockFinding("f2")])],
            prompt_builder=builder_b,
            response_model=MockClassification,
            batching_mode=BatchingMode.COUNT_BASED,
            run_id="run-1",
        )

        results = await dispatcher.dispatch([request_a, request_b])

        result_a = next(r for r in results if r.request_id == request_a.request_id)
        result_b = next(r for r in results if r.request_id == request_b.request_id)

        assert result_a.response_model_name == "MockResponse"
        assert result_a.name == "assessment"
        assert result_b.response_model_name == "MockClassification"
        assert result_b.name == "classification"

    async def test_skipped_findings_included_in_result(self) -> None:
        """Request with oversized/missing-content groups → skipped findings in result."""
        from waivern_llm.types import SkipReason

        store = AsyncInMemoryStore()
        response = MockResponse(valid=True, reason="ok")
        provider = _create_mock_provider(response)

        dispatcher = LLMDispatcher(provider=provider, store=store)

        # EXTENDED_CONTEXT mode skips groups with content=None
        valid_group: ItemGroup[MockFinding] = ItemGroup(
            items=[MockFinding("f1")], content="valid content"
        )
        missing_group: ItemGroup[MockFinding] = ItemGroup(
            items=[MockFinding("f2"), MockFinding("f3")], content=None
        )
        request = LLMRequest(
            groups=[valid_group, missing_group],
            prompt_builder=_create_mock_prompt_builder(),
            response_model=MockResponse,
            batching_mode=BatchingMode.EXTENDED_CONTEXT,
            run_id="run-1",
        )

        results = await dispatcher.dispatch([request])

        assert len(results[0].responses) == 1
        assert len(results[0].skipped) == 2
        assert all(s.reason == SkipReason.MISSING_CONTENT for s in results[0].skipped)

    async def test_built_cache_keys_populated_after_first_run(self) -> None:
        """After dispatch, request.built_cache_keys contains computed cache keys."""
        store = AsyncInMemoryStore()
        response = MockResponse(valid=True, reason="ok")
        provider = _create_mock_provider(response)
        # 1 item per batch → 2 items = 2 batches = 2 cache keys
        provider.context_window = 4385

        dispatcher = LLMDispatcher(provider=provider, store=store)
        request = _create_request(item_count=2, run_id="run-1")
        request.prompt_builder = _create_unique_prompt_builder()

        assert request.built_cache_keys is None

        await dispatcher.dispatch([request])

        cache_keys = cast("list[str]", request.built_cache_keys)
        assert len(cache_keys) == 2
        assert all(len(key) == 64 for key in cache_keys)  # SHA256 hex

    async def test_clears_cache_after_successful_sync_dispatch(self) -> None:
        """Cache empty after successful sync dispatch."""
        from waivern_llm.cache import CacheEntry

        store = AsyncInMemoryStore()
        response = MockResponse(valid=True, reason="ok")
        provider = _create_mock_provider(response)

        dispatcher = LLMDispatcher(provider=provider, store=store)
        request = _create_request(run_id="run-1")

        await dispatcher.dispatch([request])

        # Cache should be cleared after successful completion
        cache_key = CacheEntry.compute_key("test prompt", "test-model", "MockResponse")
        cached = await store.cache_get("run-1", cache_key)
        assert cached is None

    async def test_provider_error_produces_batch_error_skipped_findings(self) -> None:
        """invoke_structured() raises for one batch → affected findings get BATCH_ERROR."""
        from waivern_llm.types import SkipReason

        store = AsyncInMemoryStore()
        call_count = 0

        async def invoke_side_effect(
            _prompt: str, _response_model: type[MockResponse]
        ) -> MockResponse:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("LLM provider failed")
            return MockResponse(valid=True, reason=f"ok-{call_count}")

        provider = Mock()
        provider.model_name = "test-model"
        provider.context_window = 4385  # 1 item per batch
        provider.invoke_structured = AsyncMock(side_effect=invoke_side_effect)

        dispatcher = LLMDispatcher(provider=provider, store=store)
        request = _create_request(item_count=2, run_id="run-1")
        request.prompt_builder = _create_unique_prompt_builder()

        results = await dispatcher.dispatch([request])

        # First batch succeeded, second failed
        assert len(results[0].responses) == 1
        assert len(results[0].skipped) == 1
        assert results[0].skipped[0].reason == SkipReason.BATCH_ERROR


# =============================================================================
# Sync Mode — Resume
# =============================================================================


class TestLLMDispatcherSyncResume:
    """Tests for sync mode resume path (built_cache_keys populated)."""

    async def test_resume_uses_built_cache_keys_directly(self) -> None:
        """built_cache_keys populated + cache completed → results without planning or provider calls."""
        from waivern_llm.cache import CacheEntry

        store = AsyncInMemoryStore()
        provider = _create_mock_provider(MockResponse(valid=True, reason="unused"))

        # Pre-populate cache with completed entries
        key_1 = "aaa" * 21 + "a"  # 64-char fake key
        key_2 = "bbb" * 21 + "b"
        for key, reason in [(key_1, "cached-1"), (key_2, "cached-2")]:
            entry = CacheEntry(
                status="completed",
                response={"valid": True, "reason": reason},
                batch_id=None,
            )
            await store.cache_set("run-1", key, entry.model_dump())

        dispatcher = LLMDispatcher(provider=provider, store=store)

        # Create request with built_cache_keys already set (resume scenario)
        request = _create_request(run_id="run-1")
        request.built_cache_keys = [key_1, key_2]

        results = await dispatcher.dispatch([request])

        # Provider and prompt builder never called — resume skips planning entirely
        provider.invoke_structured.assert_not_called()
        prompt_builder = cast("Mock", request.prompt_builder)
        prompt_builder.build_prompt.assert_not_called()
        assert len(results[0].responses) == 2
        assert results[0].responses[0]["reason"] == "cached-1"
        assert results[0].responses[1]["reason"] == "cached-2"


# =============================================================================
# Batch Mode — First Run
# =============================================================================


class TestLLMDispatcherBatchFirstRun:
    """Tests for batch mode first-run dispatch."""

    async def test_batch_mode_submits_all_misses_in_single_call(self) -> None:
        """Multiple requests with misses → ONE submit_batch(), PendingBatchError, ONE BatchJob."""
        import pytest

        from waivern_llm.batch_job import BatchJob
        from waivern_llm.batch_types import BatchSubmission
        from waivern_llm.cache import CacheEntry
        from waivern_llm.errors import PendingBatchError

        store = AsyncInMemoryStore()
        submission = BatchSubmission(batch_id="batch-abc", request_count=2)
        provider = Mock()
        provider.model_name = "test-model"
        provider.context_window = 100_000
        provider.invoke_structured = AsyncMock()
        provider.submit_batch = AsyncMock(return_value=submission)
        provider.get_batch_status = AsyncMock()
        provider.get_batch_results = AsyncMock()
        provider.cancel_batch = AsyncMock()

        dispatcher = LLMDispatcher(provider=provider, store=store, batch_mode=True)

        # Two requests — each produces one cache miss
        builder_a = Mock()
        builder_a.build_prompt = Mock(return_value="prompt-A")
        request_a = LLMRequest(
            groups=[ItemGroup(items=[MockFinding("f1")])],
            prompt_builder=builder_a,
            response_model=MockResponse,
            batching_mode=BatchingMode.COUNT_BASED,
            run_id="run-1",
        )
        builder_b = Mock()
        builder_b.build_prompt = Mock(return_value="prompt-B")
        request_b = LLMRequest(
            groups=[ItemGroup(items=[MockFinding("f2")])],
            prompt_builder=builder_b,
            response_model=MockResponse,
            batching_mode=BatchingMode.COUNT_BASED,
            run_id="run-1",
        )

        with pytest.raises(PendingBatchError) as exc_info:
            await dispatcher.dispatch([request_a, request_b])

        # ONE submit_batch call with both misses
        provider.submit_batch.assert_called_once()
        batch_requests = provider.submit_batch.call_args[0][0]
        assert len(batch_requests) == 2

        # invoke_structured NOT called (batch path)
        provider.invoke_structured.assert_not_called()

        # PendingBatchError has correct batch_id
        assert "batch-abc" in exc_info.value.batch_ids

        # ONE BatchJob saved
        jobs = await BatchJob.list_for_run(store, "run-1")
        assert len(jobs) == 1
        assert jobs[0].batch_id == "batch-abc"
        assert len(jobs[0].cache_keys) == 2

        # Pending cache entries written
        for req in batch_requests:
            cached_data = await store.cache_get("run-1", req.custom_id)
            assert cached_data is not None
            cached = CacheEntry.model_validate(cached_data)
            assert cached.status == "pending"

    async def test_batch_mode_mixed_cache_states(self) -> None:
        """Completed/pending/miss → only misses submitted, pending IDs collected."""
        import pytest

        from waivern_llm.batch_types import BatchSubmission
        from waivern_llm.cache import CacheEntry
        from waivern_llm.errors import PendingBatchError

        store = AsyncInMemoryStore()
        submission = BatchSubmission(batch_id="batch-new", request_count=1)
        provider = Mock()
        provider.model_name = "test-model"
        provider.context_window = 4385  # 1 item per batch
        provider.invoke_structured = AsyncMock()
        provider.submit_batch = AsyncMock(return_value=submission)
        provider.get_batch_status = AsyncMock()
        provider.get_batch_results = AsyncMock()
        provider.cancel_batch = AsyncMock()

        # Pre-populate: prompt-1 completed, prompt-2 pending
        key_1 = CacheEntry.compute_key("prompt-1", "test-model", "MockResponse")
        await store.cache_set(
            "run-1",
            key_1,
            CacheEntry(
                status="completed",
                response={"valid": True, "reason": "cached"},
                batch_id=None,
            ).model_dump(),
        )
        key_2 = CacheEntry.compute_key("prompt-2", "test-model", "MockResponse")
        await store.cache_set(
            "run-1",
            key_2,
            CacheEntry(
                status="pending",
                response=None,
                batch_id="batch-existing",
            ).model_dump(),
        )

        dispatcher = LLMDispatcher(provider=provider, store=store, batch_mode=True)
        request = _create_request(item_count=3, run_id="run-1")
        request.prompt_builder = _create_unique_prompt_builder()

        with pytest.raises(PendingBatchError) as exc_info:
            await dispatcher.dispatch([request])

        # Only prompt-3 (the miss) was submitted
        provider.submit_batch.assert_called_once()
        batch_requests = provider.submit_batch.call_args[0][0]
        assert len(batch_requests) == 1

        # Both existing pending and new batch IDs in error
        assert "batch-existing" in exc_info.value.batch_ids
        assert "batch-new" in exc_info.value.batch_ids


# =============================================================================
# Batch Mode — Resume
# =============================================================================


class TestLLMDispatcherBatchResume:
    """Tests for batch mode resume path."""

    async def test_batch_mode_resume_returns_results_when_all_completed(self) -> None:
        """All cache entries completed → results returned, no PendingBatchError."""
        from waivern_llm.cache import CacheEntry

        store = AsyncInMemoryStore()
        provider = Mock()
        provider.model_name = "test-model"
        provider.context_window = 100_000
        provider.invoke_structured = AsyncMock()
        provider.submit_batch = AsyncMock()
        provider.get_batch_status = AsyncMock()
        provider.get_batch_results = AsyncMock()
        provider.cancel_batch = AsyncMock()

        # Pre-populate cache with completed entries
        key_1 = "aaa" * 21 + "a"
        key_2 = "bbb" * 21 + "b"
        for key, reason in [(key_1, "result-1"), (key_2, "result-2")]:
            await store.cache_set(
                "run-1",
                key,
                CacheEntry(
                    status="completed",
                    response={"valid": True, "reason": reason},
                    batch_id=None,
                ).model_dump(),
            )

        dispatcher = LLMDispatcher(provider=provider, store=store, batch_mode=True)
        request = _create_request(run_id="run-1")
        request.built_cache_keys = [key_1, key_2]

        # Should NOT raise PendingBatchError
        results = await dispatcher.dispatch([request])

        provider.submit_batch.assert_not_called()
        provider.invoke_structured.assert_not_called()
        assert len(results[0].responses) == 2
        assert results[0].responses[0]["reason"] == "result-1"
        assert results[0].responses[1]["reason"] == "result-2"


# =============================================================================
# Configuration
# =============================================================================


class TestLLMDispatcherConfiguration:
    """Tests for dispatcher configuration behaviour."""

    async def test_batch_mode_falls_back_to_sync_for_non_batch_provider(self) -> None:
        """batch_mode=True with non-BatchLLMProvider → sync path used."""
        store = AsyncInMemoryStore()
        response = MockResponse(valid=True, reason="from sync")

        # Concrete provider without batch methods — isinstance(p, BatchLLMProvider) = False
        class _SyncOnlyProvider:
            @property
            def model_name(self) -> str:
                return "test-model"

            @property
            def context_window(self) -> int:
                return 100_000

            invoke_structured = AsyncMock(return_value=response)

        provider = _SyncOnlyProvider()
        dispatcher = LLMDispatcher(
            provider=provider,
            store=store,
            batch_mode=True,  # type: ignore[arg-type]
        )
        request = _create_request(run_id="run-1")

        # Should use sync path, NOT raise PendingBatchError
        results = await dispatcher.dispatch([request])

        assert len(results[0].responses) == 1
        assert results[0].responses[0]["reason"] == "from sync"
        provider.invoke_structured.assert_called_once()


# =============================================================================
# Input Validation
# =============================================================================


class TestLLMDispatcherValidation:
    """Tests for dispatch input validation."""

    async def test_mixed_run_ids_raises_value_error(self) -> None:
        """Requests with different run_ids → ValueError before any processing."""
        import pytest

        store = AsyncInMemoryStore()
        response = MockResponse(valid=True, reason="unused")
        provider = _create_mock_provider(response)

        dispatcher = LLMDispatcher(provider=provider, store=store)
        request_a = _create_request(run_id="run-1")
        request_b = _create_request(run_id="run-2")

        with pytest.raises(ValueError, match="run_id"):
            await dispatcher.dispatch([request_a, request_b])

        # No processing should have occurred
        provider.invoke_structured.assert_not_called()

    async def test_empty_requests_returns_empty_sequence(self) -> None:
        """Empty request sequence → empty result, no errors."""
        store = AsyncInMemoryStore()
        response = MockResponse(valid=True, reason="unused")
        provider = _create_mock_provider(response)

        dispatcher = LLMDispatcher(provider=provider, store=store)

        results = await dispatcher.dispatch([])

        assert results == []
        provider.invoke_structured.assert_not_called()
