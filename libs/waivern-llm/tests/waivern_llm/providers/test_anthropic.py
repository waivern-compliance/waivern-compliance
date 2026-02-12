"""Tests for AnthropicProvider.

Business behaviour: Provides async LLM calls using Anthropic's Claude models
via LangChain, satisfying the LLMProvider protocol.
"""

import pytest
from pydantic import BaseModel

from waivern_llm.errors import LLMConfigurationError, LLMConnectionError
from waivern_llm.providers import AnthropicProvider

ANTHROPIC_ENV_VARS = ["ANTHROPIC_API_KEY", "ANTHROPIC_MODEL"]


# =============================================================================
# Initialisation
# =============================================================================


class TestAnthropicProviderInitialisation:
    """Tests for AnthropicProvider initialisation and configuration."""

    def test_initialisation_with_explicit_parameters(self) -> None:
        """Provider accepts api_key and model parameters."""
        provider = AnthropicProvider(
            api_key="test-api-key",
            model="claude-opus-4-5",
        )

        assert provider.model_name == "claude-opus-4-5"

    def test_initialisation_with_environment_variables(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Provider reads from ANTHROPIC_API_KEY and ANTHROPIC_MODEL env vars."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-api-key")
        monkeypatch.setenv("ANTHROPIC_MODEL", "claude-haiku-4-5")

        provider = AnthropicProvider()

        assert provider.model_name == "claude-haiku-4-5"

    def test_initialisation_uses_default_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Provider uses claude-sonnet-4-5 when model not specified."""
        for var in ANTHROPIC_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        provider = AnthropicProvider()

        assert provider.model_name == "claude-sonnet-4-5"

    def test_parameter_overrides_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Explicit parameters take precedence over environment variables."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
        monkeypatch.setenv("ANTHROPIC_MODEL", "env-model")

        provider = AnthropicProvider(api_key="param-key", model="param-model")

        assert provider.model_name == "param-model"

    def test_missing_api_key_raises_configuration_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Missing API key raises LLMConfigurationError with helpful message."""
        for var in ANTHROPIC_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        with pytest.raises(LLMConfigurationError) as exc_info:
            AnthropicProvider()

        assert "ANTHROPIC_API_KEY" in str(exc_info.value)


# =============================================================================
# Protocol Compliance
# =============================================================================


class TestAnthropicProviderProtocol:
    """Tests for LLMProvider protocol compliance."""

    def test_satisfies_llm_provider_protocol(self) -> None:
        """Provider satisfies LLMProvider protocol (isinstance check)."""
        from waivern_llm.providers import LLMProvider

        provider = AnthropicProvider(api_key="test-key")

        assert isinstance(provider, LLMProvider)

    def test_context_window_returns_model_capabilities(self) -> None:
        """context_window property returns value from ModelCapabilities."""
        from waivern_llm.model_capabilities import ModelCapabilities

        provider = AnthropicProvider(api_key="test-key", model="claude-sonnet-4-5")

        expected = ModelCapabilities.get("claude-sonnet-4-5").context_window
        assert provider.context_window == expected


# =============================================================================
# invoke_structured
# =============================================================================


class MockResponse(BaseModel):
    """Mock response model for testing."""

    content: str


class TestAnthropicProviderInvokeStructured:
    """Tests for invoke_structured method."""

    async def test_invoke_structured_returns_response_model(self) -> None:
        """invoke_structured returns instance of provided response model."""
        from unittest.mock import Mock, patch

        with patch("waivern_llm.providers.anthropic.ChatAnthropic") as mock_chat_class:
            mock_llm = Mock()
            mock_structured = Mock()
            mock_structured.invoke.return_value = MockResponse(content="test response")
            mock_llm.with_structured_output.return_value = mock_structured
            mock_chat_class.return_value = mock_llm

            provider = AnthropicProvider(api_key="test-key")
            result = await provider.invoke_structured("test prompt", MockResponse)

            assert isinstance(result, MockResponse)
            assert result.content == "test response"

    async def test_invoke_structured_raises_connection_error_on_failure(self) -> None:
        """invoke_structured wraps LangChain errors in LLMConnectionError."""
        from unittest.mock import Mock, patch

        with patch("waivern_llm.providers.anthropic.ChatAnthropic") as mock_chat_class:
            mock_llm = Mock()
            mock_structured = Mock()
            mock_structured.invoke.side_effect = Exception("API error")
            mock_llm.with_structured_output.return_value = mock_structured
            mock_chat_class.return_value = mock_llm

            provider = AnthropicProvider(api_key="test-key")

            with pytest.raises(LLMConnectionError) as exc_info:
                await provider.invoke_structured("test prompt", MockResponse)

            assert "API error" in str(exc_info.value)


# =============================================================================
# submit_batch
# =============================================================================


class TestAnthropicProviderSubmitBatch:
    """Tests for BatchLLMProvider.submit_batch() implementation."""

    async def test_submit_batch_creates_batch_with_correct_requests(self) -> None:
        """submit_batch builds correct request list, calls SDK, returns BatchSubmission."""
        from unittest.mock import AsyncMock, patch

        from waivern_core import JsonValue

        from waivern_llm.batch_types import BatchRequest

        mock_batch = AsyncMock()
        mock_batch.id = "batch-abc123"

        mock_async_client = AsyncMock()
        mock_async_client.beta.messages.batches.create.return_value = mock_batch

        schema: dict[str, JsonValue] = {
            "type": "object",
            "properties": {"result": {"type": "string"}},
        }
        requests = [
            BatchRequest(
                custom_id="key-1",
                prompt="Analyse this data",
                model="claude-sonnet-4-5",
                response_schema=schema,
            ),
        ]

        with patch(
            "waivern_llm.providers.anthropic.AsyncAnthropic",
            return_value=mock_async_client,
        ):
            provider = AnthropicProvider(api_key="test-key", model="claude-sonnet-4-5")
            result = await provider.submit_batch(requests)

        # Verify batch creation
        mock_async_client.beta.messages.batches.create.assert_awaited_once()
        create_kwargs = mock_async_client.beta.messages.batches.create.call_args.kwargs
        assert "requests" in create_kwargs

        request_list = create_kwargs["requests"]
        assert len(request_list) == 1

        # Verify request structure
        req = request_list[0]
        assert req["custom_id"] == "key-1"
        assert "params" in req

        params = req["params"]
        assert params["model"] == "claude-sonnet-4-5"
        assert params["max_tokens"] == 8192  # ModelCapabilities for claude-sonnet-4-5
        assert params["temperature"] == 0
        assert params["messages"] == [{"role": "user", "content": "Analyse this data"}]

        # Verify structured output config
        assert "output_config" in params
        output_config = params["output_config"]
        assert "format" in output_config
        format_spec = output_config["format"]
        assert format_spec["type"] == "json_schema"
        strict_schema = format_spec["schema"]
        assert strict_schema["type"] == "object"
        assert strict_schema["properties"] == schema["properties"]
        assert strict_schema["additionalProperties"] is False  # ensure_strict_schema

        # Verify return value
        assert result.batch_id == "batch-abc123"
        assert result.request_count == 1

    async def test_submit_batch_wraps_sdk_exception_in_connection_error(self) -> None:
        """SDK exceptions during batch submission are wrapped in LLMConnectionError."""
        from unittest.mock import AsyncMock, patch

        from waivern_core import JsonValue

        from waivern_llm.batch_types import BatchRequest

        mock_async_client = AsyncMock()
        mock_async_client.beta.messages.batches.create.side_effect = Exception(
            "API rate limit exceeded"
        )

        schema: dict[str, JsonValue] = {
            "type": "object",
            "properties": {"result": {"type": "string"}},
        }
        requests = [
            BatchRequest(
                custom_id="key-1",
                prompt="Analyse this",
                model="claude-sonnet-4-5",
                response_schema=schema,
            ),
        ]

        with patch(
            "waivern_llm.providers.anthropic.AsyncAnthropic",
            return_value=mock_async_client,
        ):
            provider = AnthropicProvider(api_key="test-key", model="claude-sonnet-4-5")

            with pytest.raises(LLMConnectionError) as exc_info:
                await provider.submit_batch(requests)

            assert "API rate limit exceeded" in str(exc_info.value)


# =============================================================================
# Batch operations (get_batch_status, get_batch_results, cancel_batch)
# =============================================================================


class TestAnthropicProviderBatchOperations:
    """Tests for remaining BatchLLMProvider methods."""

    @pytest.mark.parametrize(
        ("anthropic_status", "expected_status"),
        [
            ("in_progress", "in_progress"),
            ("canceling", "cancelled"),
            ("ended", "completed"),
        ],
    )
    async def test_get_batch_status_maps_anthropic_status_and_counts(
        self, anthropic_status: str, expected_status: str
    ) -> None:
        """get_batch_status maps Anthropic status strings to BatchStatusLiteral."""
        from unittest.mock import AsyncMock, patch

        # Create mock batch with request counts
        mock_batch = AsyncMock()
        mock_batch.processing_status = anthropic_status
        mock_batch.request_counts = AsyncMock()
        mock_batch.request_counts.succeeded = 5
        mock_batch.request_counts.errored = 2
        mock_batch.request_counts.expired = 1
        mock_batch.request_counts.canceled = 1
        mock_batch.request_counts.processing = 3

        mock_async_client = AsyncMock()
        mock_async_client.beta.messages.batches.retrieve.return_value = mock_batch

        with patch(
            "waivern_llm.providers.anthropic.AsyncAnthropic",
            return_value=mock_async_client,
        ):
            provider = AnthropicProvider(api_key="test-key", model="claude-sonnet-4-5")
            result = await provider.get_batch_status("batch-123")

        # Verify status mapping
        assert result.batch_id == "batch-123"
        assert result.status == expected_status

        # Verify count mapping
        assert result.completed_count == 5  # succeeded
        assert result.failed_count == 4  # errored + expired + canceled
        assert (
            result.total_count == 12
        )  # processing + succeeded + errored + expired + canceled

    async def test_get_batch_results_parses_mixed_outcomes(self) -> None:
        """get_batch_results parses succeeded, errored, canceled, and expired results."""
        from unittest.mock import AsyncMock, patch

        # Create mock responses for each result type
        mock_succeeded = AsyncMock()
        mock_succeeded.custom_id = "req-1"
        mock_succeeded.result.type = "succeeded"
        mock_succeeded.result.message.content = [
            AsyncMock(text='{"result": "success"}')
        ]

        mock_errored = AsyncMock()
        mock_errored.custom_id = "req-2"
        mock_errored.result.type = "errored"
        mock_errored.result.error.message = "Rate limit exceeded"

        mock_canceled = AsyncMock()
        mock_canceled.custom_id = "req-3"
        mock_canceled.result.type = "canceled"

        mock_expired = AsyncMock()
        mock_expired.custom_id = "req-4"
        mock_expired.result.type = "expired"

        # Create async iterator
        async def mock_results():
            yield mock_succeeded
            yield mock_errored
            yield mock_canceled
            yield mock_expired

        mock_async_client = AsyncMock()
        mock_async_client.beta.messages.batches.results.return_value = mock_results()

        with (
            patch(
                "waivern_llm.providers.anthropic.AsyncAnthropic",
                return_value=mock_async_client,
            ),
            patch(
                "waivern_llm.providers.anthropic.isinstance",
                side_effect=lambda obj, cls: (
                    cls.__name__ == "BetaTextBlock" if hasattr(obj, "text") else False
                ),
            ),
        ):
            provider = AnthropicProvider(api_key="test-key", model="claude-sonnet-4-5")
            results = await provider.get_batch_results("batch-123")

        # Verify we got 4 results
        assert len(results) == 4

        # Verify succeeded result
        assert results[0].custom_id == "req-1"
        assert results[0].status == "completed"
        assert results[0].response == {"result": "success"}
        assert results[0].error is None

        # Verify errored result
        assert results[1].custom_id == "req-2"
        assert results[1].status == "failed"
        assert results[1].response is None
        assert results[1].error == "Rate limit exceeded"

        # Verify canceled result
        assert results[2].custom_id == "req-3"
        assert results[2].status == "failed"
        assert results[2].response is None
        assert results[2].error == "Request was cancelled"

        # Verify expired result
        assert results[3].custom_id == "req-4"
        assert results[3].status == "failed"
        assert results[3].response is None
        assert results[3].error == "Request expired"

    async def test_cancel_batch_calls_sdk(self) -> None:
        """cancel_batch calls client.beta.messages.batches.cancel with the batch_id."""
        from unittest.mock import AsyncMock, patch

        mock_async_client = AsyncMock()
        mock_async_client.beta.messages.batches.cancel.return_value = AsyncMock()

        with patch(
            "waivern_llm.providers.anthropic.AsyncAnthropic",
            return_value=mock_async_client,
        ):
            provider = AnthropicProvider(api_key="test-key", model="claude-sonnet-4-5")
            await provider.cancel_batch("batch-123")

        # Verify SDK method was called with correct batch_id
        mock_async_client.beta.messages.batches.cancel.assert_awaited_once_with(
            "batch-123"
        )

    async def test_batch_operation_wraps_sdk_exception_in_connection_error(
        self,
    ) -> None:
        """SDK exceptions during batch operations are wrapped in LLMConnectionError."""
        from unittest.mock import AsyncMock, patch

        mock_async_client = AsyncMock()
        mock_async_client.beta.messages.batches.retrieve.side_effect = Exception(
            "Network timeout"
        )

        with (
            patch(
                "waivern_llm.providers.anthropic.AsyncAnthropic",
                return_value=mock_async_client,
            ),
            pytest.raises(LLMConnectionError) as exc_info,
        ):
            provider = AnthropicProvider(api_key="test-key", model="claude-sonnet-4-5")
            await provider.get_batch_status("batch-123")

        # Verify the exception message includes the original error
        assert "Network timeout" in str(exc_info.value)


class TestAnthropicProviderProtocolCompliance:
    """Tests for BatchLLMProvider protocol compliance."""

    def test_satisfies_batch_llm_provider_protocol(self) -> None:
        """Provider satisfies BatchLLMProvider protocol (isinstance check)."""
        from waivern_llm.providers.protocol import BatchLLMProvider

        provider = AnthropicProvider(api_key="test-key")

        assert isinstance(provider, BatchLLMProvider)
