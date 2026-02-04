"""Tests for OpenAIProvider.

Business behaviour: Provides async LLM calls using OpenAI's models
via LangChain, satisfying the LLMProvider protocol.
"""

import pytest
from pydantic import BaseModel

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
    """Tests for LLMProvider protocol compliance."""

    def test_satisfies_llm_provider_protocol(self) -> None:
        """Provider satisfies LLMProvider protocol (isinstance check)."""
        from waivern_llm.providers import LLMProvider

        provider = OpenAIProvider(api_key="test-key")

        assert isinstance(provider, LLMProvider)

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
