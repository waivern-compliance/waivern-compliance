"""Tests for GoogleProvider.

Business behaviour: Provides async LLM calls using Google's Gemini models
via LangChain, satisfying the LLMProvider protocol.
"""

import pytest
from pydantic import BaseModel

from waivern_llm.errors import LLMConfigurationError, LLMConnectionError
from waivern_llm.providers import GoogleProvider

GOOGLE_ENV_VARS = ["GOOGLE_API_KEY", "GOOGLE_MODEL"]


# =============================================================================
# Initialisation
# =============================================================================


class TestGoogleProviderInitialisation:
    """Tests for GoogleProvider initialisation and configuration."""

    def test_initialisation_with_explicit_parameters(self) -> None:
        """Provider accepts api_key and model parameters."""
        provider = GoogleProvider(
            api_key="test-api-key",
            model="gemini-3-pro",
        )

        assert provider.model_name == "gemini-3-pro"

    def test_initialisation_with_environment_variables(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Provider reads from GOOGLE_API_KEY and GOOGLE_MODEL env vars."""
        monkeypatch.setenv("GOOGLE_API_KEY", "env-api-key")
        monkeypatch.setenv("GOOGLE_MODEL", "gemini-2.5-pro")

        provider = GoogleProvider()

        assert provider.model_name == "gemini-2.5-pro"

    def test_initialisation_uses_default_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Provider uses gemini-2.5-flash when model not specified."""
        for var in GOOGLE_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

        provider = GoogleProvider()

        assert provider.model_name == "gemini-2.5-flash"

    def test_parameter_overrides_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Explicit parameters take precedence over environment variables."""
        monkeypatch.setenv("GOOGLE_API_KEY", "env-key")
        monkeypatch.setenv("GOOGLE_MODEL", "env-model")

        provider = GoogleProvider(api_key="param-key", model="param-model")

        assert provider.model_name == "param-model"

    def test_missing_api_key_raises_configuration_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Missing API key raises LLMConfigurationError with helpful message."""
        for var in GOOGLE_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        with pytest.raises(LLMConfigurationError) as exc_info:
            GoogleProvider()

        assert "GOOGLE_API_KEY" in str(exc_info.value)


# =============================================================================
# Protocol Compliance
# =============================================================================


class TestGoogleProviderProtocol:
    """Tests for LLMProvider protocol compliance."""

    def test_satisfies_llm_provider_protocol(self) -> None:
        """Provider satisfies LLMProvider protocol (isinstance check)."""
        from waivern_llm.providers import LLMProvider

        provider = GoogleProvider(api_key="test-key")

        assert isinstance(provider, LLMProvider)

    def test_context_window_returns_model_capabilities(self) -> None:
        """context_window property returns value from ModelCapabilities."""
        from waivern_llm.model_capabilities import ModelCapabilities

        provider = GoogleProvider(api_key="test-key", model="gemini-2.5-flash")

        expected = ModelCapabilities.get("gemini-2.5-flash").context_window
        assert provider.context_window == expected


# =============================================================================
# invoke_structured
# =============================================================================


class MockResponse(BaseModel):
    """Mock response model for testing."""

    content: str


class TestGoogleProviderInvokeStructured:
    """Tests for invoke_structured method."""

    async def test_invoke_structured_returns_response_model(self) -> None:
        """invoke_structured returns instance of provided response model."""
        from unittest.mock import Mock, patch

        with patch(
            "waivern_llm.providers.google.ChatGoogleGenerativeAI"
        ) as mock_chat_class:
            mock_llm = Mock()
            mock_structured = Mock()
            mock_structured.invoke.return_value = MockResponse(content="test response")
            mock_llm.with_structured_output.return_value = mock_structured
            mock_chat_class.return_value = mock_llm

            provider = GoogleProvider(api_key="test-key")
            result = await provider.invoke_structured("test prompt", MockResponse)

            assert isinstance(result, MockResponse)
            assert result.content == "test response"

    async def test_invoke_structured_raises_connection_error_on_failure(self) -> None:
        """invoke_structured wraps LangChain errors in LLMConnectionError."""
        from unittest.mock import Mock, patch

        with patch(
            "waivern_llm.providers.google.ChatGoogleGenerativeAI"
        ) as mock_chat_class:
            mock_llm = Mock()
            mock_structured = Mock()
            mock_structured.invoke.side_effect = Exception("API error")
            mock_llm.with_structured_output.return_value = mock_structured
            mock_chat_class.return_value = mock_llm

            provider = GoogleProvider(api_key="test-key")

            with pytest.raises(LLMConnectionError) as exc_info:
                await provider.invoke_structured("test prompt", MockResponse)

            assert "API error" in str(exc_info.value)


# =============================================================================
# submit_batch
# =============================================================================


class TestGoogleProviderSubmitBatch:
    """Tests for BatchLLMProvider.submit_batch() implementation."""

    async def test_submit_batch_uploads_jsonl_and_creates_batch(self) -> None:
        """submit_batch builds JSONL, uploads file, creates batch, returns BatchSubmission."""
        import io
        import json
        from unittest.mock import AsyncMock, Mock, patch

        from waivern_core import JsonValue

        from waivern_llm.batch_types import BatchRequest

        # Mock file upload
        mock_uploaded_file = Mock()
        mock_uploaded_file.name = "files/uploaded-123"

        # Mock batch job
        mock_batch_job = Mock()
        mock_batch_job.name = "batches/batch-abc123"

        mock_client = Mock()
        mock_client.aio.files.upload = AsyncMock(return_value=mock_uploaded_file)
        mock_client.aio.batches.create = AsyncMock(return_value=mock_batch_job)

        schema: dict[str, JsonValue] = {
            "type": "object",
            "properties": {"result": {"type": "string"}},
        }
        requests = [
            BatchRequest(
                custom_id="key-1",
                prompt="Analyse this data",
                model="gemini-2.5-flash",
                response_schema=schema,
            ),
        ]

        with patch(
            "waivern_llm.providers.google.genai.Client",
            return_value=mock_client,
        ):
            provider = GoogleProvider(api_key="test-key", model="gemini-2.5-flash")
            result = await provider.submit_batch(requests)

        # Verify file upload
        mock_client.aio.files.upload.assert_awaited_once()
        upload_kwargs = mock_client.aio.files.upload.call_args.kwargs
        assert upload_kwargs["config"]["mime_type"] == "application/jsonl"

        # Verify JSONL content
        uploaded_file = upload_kwargs["file"]
        assert isinstance(uploaded_file, io.BytesIO)
        uploaded_file.seek(0)
        line = json.loads(uploaded_file.readline())
        assert line["key"] == "key-1"
        assert line["request"]["contents"] == [
            {"role": "user", "parts": [{"text": "Analyse this data"}]}
        ]
        gen_config = line["request"]["generation_config"]
        assert gen_config["response_mime_type"] == "application/json"
        assert gen_config["response_schema"]["type"] == "OBJECT"
        assert gen_config["temperature"] == 0

        # Verify batch creation
        mock_client.aio.batches.create.assert_awaited_once()
        create_kwargs = mock_client.aio.batches.create.call_args.kwargs
        assert create_kwargs["model"] == "gemini-2.5-flash"
        assert create_kwargs["src"] == "files/uploaded-123"

        # Verify return value
        assert result.batch_id == "batches/batch-abc123"
        assert result.request_count == 1

    async def test_submit_batch_wraps_sdk_exception_in_connection_error(self) -> None:
        """SDK exceptions during batch submission are wrapped in LLMConnectionError."""
        from unittest.mock import AsyncMock, Mock, patch

        from waivern_core import JsonValue

        from waivern_llm.batch_types import BatchRequest

        mock_client = Mock()
        mock_client.aio.files.upload = AsyncMock(
            side_effect=Exception("API rate limit exceeded")
        )

        schema: dict[str, JsonValue] = {
            "type": "object",
            "properties": {"result": {"type": "string"}},
        }
        requests = [
            BatchRequest(
                custom_id="key-1",
                prompt="Analyse this",
                model="gemini-2.5-flash",
                response_schema=schema,
            ),
        ]

        with patch(
            "waivern_llm.providers.google.genai.Client",
            return_value=mock_client,
        ):
            provider = GoogleProvider(api_key="test-key", model="gemini-2.5-flash")

            with pytest.raises(LLMConnectionError) as exc_info:
                await provider.submit_batch(requests)

            assert "API rate limit exceeded" in str(exc_info.value)


# =============================================================================
# Batch operations (get_batch_status, get_batch_results, cancel_batch)
# =============================================================================


class TestGoogleProviderBatchOperations:
    """Tests for remaining BatchLLMProvider methods."""

    @pytest.mark.parametrize(
        ("gemini_state", "expected_status"),
        [
            ("JOB_STATE_PENDING", "submitted"),
            ("JOB_STATE_QUEUED", "submitted"),
            ("JOB_STATE_RUNNING", "in_progress"),
            ("JOB_STATE_SUCCEEDED", "completed"),
            ("JOB_STATE_FAILED", "failed"),
            ("JOB_STATE_CANCELLING", "cancelled"),
            ("JOB_STATE_CANCELLED", "cancelled"),
            ("JOB_STATE_EXPIRED", "expired"),
            ("JOB_STATE_PARTIALLY_SUCCEEDED", "completed"),
            ("JOB_STATE_UPDATING", "in_progress"),
        ],
    )
    async def test_get_batch_status_maps_gemini_state(
        self, gemini_state: str, expected_status: str
    ) -> None:
        """get_batch_status maps Gemini JobState values to BatchStatusLiteral."""
        from unittest.mock import AsyncMock, Mock, patch

        from google.genai.types import JobState

        mock_batch_job = Mock()
        mock_batch_job.state = JobState(gemini_state)

        mock_client = Mock()
        mock_client.aio.batches.get = AsyncMock(return_value=mock_batch_job)

        with patch(
            "waivern_llm.providers.google.genai.Client",
            return_value=mock_client,
        ):
            provider = GoogleProvider(api_key="test-key", model="gemini-2.5-flash")
            result = await provider.get_batch_status("batches/test-123")

        assert result.batch_id == "batches/test-123"
        assert result.status == expected_status

    async def test_get_batch_results_parses_successful_responses(self) -> None:
        """get_batch_results parses JSONL output file into BatchResult list."""
        import json
        from unittest.mock import AsyncMock, Mock, patch

        # Build a two-line JSONL output matching Gemini's response format
        line1 = json.dumps(
            {
                "key": "key-1",
                "response": {
                    "candidates": [
                        {"content": {"parts": [{"text": '{"result": "ok"}'}]}}
                    ]
                },
            }
        )
        line2 = json.dumps({"key": "key-2", "error": {"message": "quota exceeded"}})
        output_bytes = f"{line1}\n{line2}\n".encode()

        mock_batch_job = Mock()
        mock_batch_job.dest = Mock()
        mock_batch_job.dest.file_name = "files/output-456"

        mock_client = Mock()
        mock_client.aio.batches.get = AsyncMock(return_value=mock_batch_job)
        mock_client.aio.files.download = AsyncMock(return_value=output_bytes)

        with patch(
            "waivern_llm.providers.google.genai.Client",
            return_value=mock_client,
        ):
            provider = GoogleProvider(api_key="test-key", model="gemini-2.5-flash")
            results = await provider.get_batch_results("batches/test-123")

        assert len(results) == 2

        # First result: successful parse
        assert results[0].custom_id == "key-1"
        assert results[0].status == "completed"
        assert results[0].response == {"result": "ok"}
        assert results[0].error is None

        # Second result: error response
        assert results[1].custom_id == "key-2"
        assert results[1].status == "failed"
        assert results[1].response is None
        assert "quota exceeded" in (results[1].error or "")

    async def test_get_batch_results_raises_on_missing_output_file(self) -> None:
        """get_batch_results raises LLMConnectionError when dest.file_name is None."""
        from unittest.mock import AsyncMock, Mock, patch

        mock_batch_job = Mock()
        mock_batch_job.dest = Mock()
        mock_batch_job.dest.file_name = None

        mock_client = Mock()
        mock_client.aio.batches.get = AsyncMock(return_value=mock_batch_job)

        with patch(
            "waivern_llm.providers.google.genai.Client",
            return_value=mock_client,
        ):
            provider = GoogleProvider(api_key="test-key", model="gemini-2.5-flash")

            with pytest.raises(LLMConnectionError) as exc_info:
                await provider.get_batch_results("batches/test-123")

            assert "no output file" in str(exc_info.value).lower()

    async def test_cancel_batch_calls_sdk(self) -> None:
        """cancel_batch calls client.aio.batches.cancel with the batch name."""
        from unittest.mock import AsyncMock, Mock, patch

        mock_client = Mock()
        mock_client.aio.batches.cancel = AsyncMock()

        with patch(
            "waivern_llm.providers.google.genai.Client",
            return_value=mock_client,
        ):
            provider = GoogleProvider(api_key="test-key", model="gemini-2.5-flash")
            await provider.cancel_batch("batches/test-123")

        mock_client.aio.batches.cancel.assert_awaited_once_with(name="batches/test-123")

    async def test_batch_operation_wraps_sdk_exception_in_connection_error(
        self,
    ) -> None:
        """SDK exceptions during batch operations are wrapped in LLMConnectionError."""
        from unittest.mock import AsyncMock, Mock, patch

        mock_client = Mock()
        mock_client.aio.batches.get = AsyncMock(
            side_effect=Exception("network timeout")
        )

        with patch(
            "waivern_llm.providers.google.genai.Client",
            return_value=mock_client,
        ):
            provider = GoogleProvider(api_key="test-key", model="gemini-2.5-flash")

            with pytest.raises(LLMConnectionError) as exc_info:
                await provider.get_batch_status("batches/test-123")

            assert "network timeout" in str(exc_info.value)


class TestGoogleProviderProtocolCompliance:
    """Tests for BatchLLMProvider protocol compliance."""

    def test_satisfies_batch_llm_provider_protocol(self) -> None:
        """Provider satisfies BatchLLMProvider protocol (isinstance check)."""
        from waivern_llm.providers import BatchLLMProvider

        provider = GoogleProvider(api_key="test-key")

        assert isinstance(provider, BatchLLMProvider)
