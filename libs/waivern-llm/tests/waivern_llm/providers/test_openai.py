"""Tests for OpenAIProvider.

Business behaviour: Provides async LLM calls using OpenAI's models
via LangChain, satisfying the LLMProvider protocol.
"""

import pytest
from pydantic import BaseModel
from waivern_core import JsonValue

from waivern_llm.errors import LLMConfigurationError, LLMConnectionError
from waivern_llm.providers import OpenAIProvider

OPENAI_ENV_VARS = ["OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL"]


# =============================================================================
# Initialisation
# =============================================================================


class TestOpenAIProviderInitialisation:
    """Tests for OpenAIProvider initialisation and configuration."""

    def test_initialisation_with_explicit_parameters(self) -> None:
        """Provider accepts api_key and model parameters."""
        provider = OpenAIProvider(
            api_key="test-api-key",
            model="gpt-5",
        )

        assert provider.model_name == "gpt-5"

    def test_initialisation_with_environment_variables(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Provider reads from OPENAI_API_KEY and OPENAI_MODEL env vars."""
        monkeypatch.setenv("OPENAI_API_KEY", "env-api-key")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")

        provider = OpenAIProvider()

        assert provider.model_name == "gpt-4o-mini"

    def test_initialisation_uses_default_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Provider uses gpt-4o when model not specified."""
        for var in OPENAI_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        provider = OpenAIProvider()

        assert provider.model_name == "gpt-4o"

    def test_parameter_overrides_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Explicit parameters take precedence over environment variables."""
        monkeypatch.setenv("OPENAI_API_KEY", "env-key")
        monkeypatch.setenv("OPENAI_MODEL", "env-model")

        provider = OpenAIProvider(api_key="param-key", model="param-model")

        assert provider.model_name == "param-model"

    def test_missing_api_key_raises_configuration_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Missing API key raises LLMConfigurationError with helpful message."""
        for var in OPENAI_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        with pytest.raises(LLMConfigurationError) as exc_info:
            OpenAIProvider()

        assert "OPENAI_API_KEY" in str(exc_info.value)

    def test_base_url_allows_missing_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Provider allows missing API key when base_url is set (local LLMs)."""
        for var in OPENAI_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        provider = OpenAIProvider(base_url="http://localhost:8000")

        assert provider.model_name == "gpt-4o"


# =============================================================================
# Protocol Compliance
# =============================================================================


class TestOpenAIProviderProtocol:
    """Tests for LLMProvider and BatchLLMProvider protocol compliance."""

    def test_satisfies_llm_provider_protocol(self) -> None:
        """Provider satisfies LLMProvider protocol (isinstance check)."""
        from waivern_llm.providers import LLMProvider

        provider = OpenAIProvider(api_key="test-key")

        assert isinstance(provider, LLMProvider)

    def test_satisfies_batch_llm_provider_protocol(self) -> None:
        """Provider satisfies BatchLLMProvider protocol (isinstance check)."""
        from waivern_llm.providers.protocol import BatchLLMProvider

        provider = OpenAIProvider(api_key="test-key")

        assert isinstance(provider, BatchLLMProvider)

    def test_context_window_returns_model_capabilities(self) -> None:
        """context_window property returns value from ModelCapabilities."""
        from waivern_llm.model_capabilities import ModelCapabilities

        provider = OpenAIProvider(api_key="test-key", model="gpt-4o")

        expected = ModelCapabilities.get("gpt-4o").context_window
        assert provider.context_window == expected


# =============================================================================
# invoke_structured
# =============================================================================


class MockResponse(BaseModel):
    """Mock response model for testing."""

    content: str


class TestOpenAIProviderInvokeStructured:
    """Tests for invoke_structured method."""

    async def test_invoke_structured_returns_response_model(self) -> None:
        """invoke_structured returns instance of provided response model."""
        from unittest.mock import Mock, patch

        with patch("waivern_llm.providers.openai.ChatOpenAI") as mock_chat_class:
            mock_llm = Mock()
            mock_structured = Mock()
            mock_structured.invoke.return_value = MockResponse(content="test response")
            mock_llm.with_structured_output.return_value = mock_structured
            mock_chat_class.return_value = mock_llm

            provider = OpenAIProvider(api_key="test-key")
            result = await provider.invoke_structured("test prompt", MockResponse)

            assert isinstance(result, MockResponse)
            assert result.content == "test response"

    async def test_invoke_structured_raises_connection_error_on_failure(self) -> None:
        """invoke_structured wraps LangChain errors in LLMConnectionError."""
        from unittest.mock import Mock, patch

        with patch("waivern_llm.providers.openai.ChatOpenAI") as mock_chat_class:
            mock_llm = Mock()
            mock_structured = Mock()
            mock_structured.invoke.side_effect = Exception("API error")
            mock_llm.with_structured_output.return_value = mock_structured
            mock_chat_class.return_value = mock_llm

            provider = OpenAIProvider(api_key="test-key")

            with pytest.raises(LLMConnectionError) as exc_info:
                await provider.invoke_structured("test prompt", MockResponse)

            assert "API error" in str(exc_info.value)


# =============================================================================
# submit_batch
# =============================================================================


class TestOpenAIProviderSubmitBatch:
    """Tests for BatchLLMProvider.submit_batch() implementation."""

    async def test_submit_batch_uploads_jsonl_and_creates_batch(self) -> None:
        """submit_batch builds JSONL, uploads file, creates batch, returns BatchSubmission."""
        import json
        from unittest.mock import AsyncMock, patch

        from waivern_llm.batch_types import BatchRequest

        mock_file = AsyncMock()
        mock_file.id = "file-abc123"

        mock_batch = AsyncMock()
        mock_batch.id = "batch-xyz789"

        mock_async_client = AsyncMock()
        mock_async_client.files.create.return_value = mock_file
        mock_async_client.batches.create.return_value = mock_batch

        schema: dict[str, JsonValue] = {
            "type": "object",
            "properties": {"result": {"type": "string"}},
        }
        requests = [
            BatchRequest(
                custom_id="key-1",
                prompt="Analyse this data",
                model="gpt-4o",
                response_schema=schema,
            ),
        ]

        with patch(
            "waivern_llm.providers.openai.AsyncOpenAI", return_value=mock_async_client
        ):
            provider = OpenAIProvider(api_key="test-key", model="gpt-4o")
            result = await provider.submit_batch(requests)

        # Verify file upload
        mock_async_client.files.create.assert_awaited_once()
        upload_kwargs = mock_async_client.files.create.call_args.kwargs
        assert upload_kwargs["purpose"] == "batch"

        # Parse and verify JSONL content
        uploaded_file = upload_kwargs["file"]
        jsonl_content = uploaded_file.read().decode("utf-8").strip()
        line = json.loads(jsonl_content)

        assert line["custom_id"] == "key-1"
        assert line["method"] == "POST"
        assert line["url"] == "/v1/chat/completions"
        assert line["body"]["model"] == "gpt-4o"
        assert line["body"]["messages"] == [
            {"role": "user", "content": "Analyse this data"}
        ]
        assert line["body"]["temperature"] == 0
        assert line["body"]["max_tokens"] == 16_384
        assert line["body"]["response_format"]["type"] == "json_schema"
        assert line["body"]["response_format"]["json_schema"]["schema"] == schema
        assert line["body"]["response_format"]["json_schema"]["strict"] is True

        # Verify batch creation
        mock_async_client.batches.create.assert_awaited_once()
        batch_kwargs = mock_async_client.batches.create.call_args.kwargs
        assert batch_kwargs["input_file_id"] == "file-abc123"
        assert batch_kwargs["endpoint"] == "/v1/chat/completions"
        assert batch_kwargs["completion_window"] == "24h"

        # Verify return value
        assert result.batch_id == "batch-xyz789"
        assert result.request_count == 1

    async def test_submit_batch_wraps_sdk_exception_in_connection_error(self) -> None:
        """SDK exceptions during batch submission are wrapped in LLMConnectionError."""
        from unittest.mock import AsyncMock, patch

        from waivern_llm.batch_types import BatchRequest

        mock_async_client = AsyncMock()
        mock_async_client.files.create.side_effect = Exception("Upload failed")

        schema: dict[str, JsonValue] = {
            "type": "object",
            "properties": {"result": {"type": "string"}},
        }
        requests = [
            BatchRequest(
                custom_id="key-1",
                prompt="Analyse this",
                model="gpt-4o",
                response_schema=schema,
            ),
        ]

        with patch(
            "waivern_llm.providers.openai.AsyncOpenAI", return_value=mock_async_client
        ):
            provider = OpenAIProvider(api_key="test-key", model="gpt-4o")

            with pytest.raises(LLMConnectionError) as exc_info:
                await provider.submit_batch(requests)

            assert "Upload failed" in str(exc_info.value)


# =============================================================================
# Batch operations (get_batch_status, get_batch_results, cancel_batch)
# =============================================================================


class TestOpenAIProviderBatchOperations:
    """Tests for the remaining BatchLLMProvider methods."""

    @pytest.mark.parametrize(
        ("openai_status", "expected_status"),
        [
            ("validating", "submitted"),
            ("in_progress", "in_progress"),
            ("finalizing", "in_progress"),
            ("completed", "completed"),
            ("failed", "failed"),
            ("expired", "expired"),
            ("cancelling", "cancelled"),
            ("cancelled", "cancelled"),
        ],
    )
    async def test_get_batch_status_maps_openai_status_and_counts(
        self, openai_status: str, expected_status: str
    ) -> None:
        """get_batch_status maps OpenAI status strings to BatchStatusLiteral."""
        from unittest.mock import AsyncMock, patch

        mock_batch = AsyncMock()
        mock_batch.status = openai_status
        mock_batch.request_counts.completed = 5
        mock_batch.request_counts.failed = 1
        mock_batch.request_counts.total = 10

        mock_async_client = AsyncMock()
        mock_async_client.batches.retrieve.return_value = mock_batch

        with patch(
            "waivern_llm.providers.openai.AsyncOpenAI", return_value=mock_async_client
        ):
            provider = OpenAIProvider(api_key="test-key", model="gpt-4o")
            result = await provider.get_batch_status("batch-123")

        assert result.batch_id == "batch-123"
        assert result.status == expected_status
        assert result.completed_count == 5
        assert result.failed_count == 1
        assert result.total_count == 10

    async def test_get_batch_results_parses_mixed_outcomes(self) -> None:
        """get_batch_results parses successful, error, and non-200 result lines."""
        import json
        from unittest.mock import AsyncMock, patch

        # Three JSONL lines: success, per-line error, non-200
        lines = [
            json.dumps(
                {
                    "id": "resp-1",
                    "custom_id": "key-1",
                    "response": {
                        "status_code": 200,
                        "body": {
                            "choices": [{"message": {"content": '{"result": "valid"}'}}]
                        },
                    },
                    "error": None,
                }
            ),
            json.dumps(
                {
                    "id": "resp-2",
                    "custom_id": "key-2",
                    "response": None,
                    "error": {"message": "Content policy violation"},
                }
            ),
            json.dumps(
                {
                    "id": "resp-3",
                    "custom_id": "key-3",
                    "response": {"status_code": 429, "body": {}},
                    "error": None,
                }
            ),
        ]
        output_jsonl = "\n".join(lines)

        mock_batch = AsyncMock()
        mock_batch.output_file_id = "file-output-123"

        mock_content = AsyncMock()
        mock_content.text = output_jsonl

        mock_async_client = AsyncMock()
        mock_async_client.batches.retrieve.return_value = mock_batch
        mock_async_client.files.content.return_value = mock_content

        with patch(
            "waivern_llm.providers.openai.AsyncOpenAI", return_value=mock_async_client
        ):
            provider = OpenAIProvider(api_key="test-key", model="gpt-4o")
            results = await provider.get_batch_results("batch-123")

        assert len(results) == 3

        # Successful response
        assert results[0].custom_id == "key-1"
        assert results[0].status == "completed"
        assert results[0].response == {"result": "valid"}
        assert results[0].error is None

        # Per-line error
        assert results[1].custom_id == "key-2"
        assert results[1].status == "failed"
        assert results[1].response is None
        assert results[1].error == "Content policy violation"

        # Non-200 status code
        assert results[2].custom_id == "key-3"
        assert results[2].status == "failed"
        assert results[2].response is None
        assert "429" in (results[2].error or "")

    async def test_cancel_batch_calls_sdk(self) -> None:
        """cancel_batch calls client.batches.cancel with the batch_id."""
        from unittest.mock import AsyncMock, patch

        mock_async_client = AsyncMock()

        with patch(
            "waivern_llm.providers.openai.AsyncOpenAI", return_value=mock_async_client
        ):
            provider = OpenAIProvider(api_key="test-key", model="gpt-4o")
            result = await provider.cancel_batch("batch-123")

        assert result is None
        mock_async_client.batches.cancel.assert_awaited_once_with("batch-123")

    async def test_batch_operation_wraps_sdk_exception_in_connection_error(
        self,
    ) -> None:
        """SDK exceptions during batch operations are wrapped in LLMConnectionError."""
        from unittest.mock import AsyncMock, patch

        mock_async_client = AsyncMock()
        mock_async_client.batches.retrieve.side_effect = Exception("Network timeout")

        with patch(
            "waivern_llm.providers.openai.AsyncOpenAI", return_value=mock_async_client
        ):
            provider = OpenAIProvider(api_key="test-key", model="gpt-4o")

            with pytest.raises(LLMConnectionError) as exc_info:
                await provider.get_batch_status("batch-123")

            assert "Network timeout" in str(exc_info.value)
