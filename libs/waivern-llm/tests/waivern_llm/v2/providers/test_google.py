"""Tests for GoogleProvider.

Business behaviour: Provides async LLM calls using Google's Gemini models
via LangChain, satisfying the LLMProvider protocol.
"""

import pytest
from pydantic import BaseModel

from waivern_llm.errors import LLMConfigurationError, LLMConnectionError
from waivern_llm.v2.providers import GoogleProvider

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
        from waivern_llm.v2.providers import LLMProvider

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
            "waivern_llm.v2.providers.google.ChatGoogleGenerativeAI"
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
            "waivern_llm.v2.providers.google.ChatGoogleGenerativeAI"
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
