"""Tests for Anthropic LLM service implementation."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from langchain_core.messages import AIMessage

from waivern_llm import AnthropicLLMService, LLMConfigurationError

ANTHROPIC_ENV_VARS = ["ANTHROPIC_API_KEY", "ANTHROPIC_MODEL"]


class TestAnthropicLLMServiceInitialisation:
    """Test AnthropicLLMService initialisation and configuration."""

    def test_initialisation_with_provided_parameters(self) -> None:
        """Test service initialisation with explicitly provided parameters."""
        service = AnthropicLLMService(
            model_name="claude-3-sonnet-20240229", api_key="test-api-key"
        )

        assert service.model_name == "claude-3-sonnet-20240229"
        # API key is private - service creation without error indicates it was set

    def test_initialisation_with_environment_variables(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test service initialisation using environment variables."""
        monkeypatch.setenv("ANTHROPIC_MODEL", "claude-3-opus-20240229")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-api-key")

        service = AnthropicLLMService()

        assert service.model_name == "claude-3-opus-20240229"
        # API key is private - service creation without error indicates it was set

    def test_initialisation_with_default_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test service initialisation uses default model when not specified."""
        # Clear ANTHROPIC_MODEL and set ANTHROPIC_API_KEY to ensure default is used
        for var in ANTHROPIC_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        service = AnthropicLLMService()

        assert service.model_name == "claude-sonnet-4-5-20250929"
        # API key is private - service creation without error indicates it was set

    def test_initialisation_parameter_overrides_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that explicit parameters override environment variables."""
        monkeypatch.setenv("ANTHROPIC_MODEL", "env-model")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")

        service = AnthropicLLMService(model_name="param-model", api_key="param-key")

        assert service.model_name == "param-model"
        # API key is private - service creation without error indicates it was set

    def test_initialisation_missing_api_key_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that missing API key raises configuration error."""
        for var in ANTHROPIC_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        with pytest.raises(LLMConfigurationError) as exc_info:
            AnthropicLLMService()

        assert "Anthropic API key is required" in str(exc_info.value)
        assert "ANTHROPIC_API_KEY" in str(exc_info.value)

    def test_initialisation_empty_api_key_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that empty API key raises configuration error."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")

        with pytest.raises(LLMConfigurationError) as exc_info:
            AnthropicLLMService()

        assert "Anthropic API key is required" in str(exc_info.value)


class TestAnthropicLLMServiceInvoke:
    """Test AnthropicLLMService invoke functionality."""

    @pytest.fixture
    def service_with_mock_api(self) -> AnthropicLLMService:
        """Create service instance with mocked API for testing."""
        return AnthropicLLMService(
            model_name="claude-3-sonnet-20240229", api_key="test-api-key"
        )

    def test_successful_invoke(
        self, service_with_mock_api: AnthropicLLMService
    ) -> None:
        """Test successful LLM invocation returns expected result."""
        prompt = "Identify personal data in: John Smith lives at 123 Main Street"
        expected_response = (
            "Personal data found: Name (John Smith), Address (123 Main Street)"
        )

        mock_response = AIMessage(content=expected_response)

        with patch("waivern_llm.anthropic.ChatAnthropic") as mock_chat:
            mock_llm = Mock()
            mock_llm.invoke.return_value = mock_response
            mock_chat.return_value = mock_llm

            result = service_with_mock_api.invoke(prompt)

            assert result == expected_response
            assert isinstance(result, str)

            # Verify the LLM was called with the prompt
            mock_llm.invoke.assert_called_once_with(prompt)

    def test_invoke_with_complex_response_content(
        self, service_with_mock_api: AnthropicLLMService
    ) -> None:
        """Test invoke handles complex response content structures."""
        prompt = "Analyse this text: Sample text for analysis"

        # Test with list content structure
        mock_response = AIMessage(
            content=[
                {"type": "text", "text": "Analysis result: "},
                {"type": "text", "text": "Complex content structure"},
            ]
        )

        with patch("waivern_llm.anthropic.ChatAnthropic") as mock_chat:
            mock_llm = Mock()
            mock_llm.invoke.return_value = mock_response
            mock_chat.return_value = mock_llm

            result = service_with_mock_api.invoke(prompt)

            assert "Analysis result:" in result
            assert "Complex content structure" in result
            assert isinstance(result, str)


class TestAnthropicLLMServiceReusability:
    """Test AnthropicLLMService instance reusability."""

    def test_service_can_be_used_multiple_times(self) -> None:
        """Test that service instance can be reused for multiple operations."""
        service = AnthropicLLMService(
            model_name="claude-3-sonnet-20240229", api_key="test-api-key"
        )

        mock_response1 = AIMessage(content="First response")
        mock_response2 = AIMessage(content="Second response")

        with patch("waivern_llm.anthropic.ChatAnthropic") as mock_chat:
            mock_llm = Mock()
            mock_llm.invoke.side_effect = [mock_response1, mock_response2]
            mock_chat.return_value = mock_llm

            # First operation
            result1 = service.invoke("prompt1")
            assert result1 == "First response"

            # Second operation
            result2 = service.invoke("prompt2")
            assert result2 == "Second response"

            # Verify both calls were made
            assert mock_llm.invoke.call_count == 2
