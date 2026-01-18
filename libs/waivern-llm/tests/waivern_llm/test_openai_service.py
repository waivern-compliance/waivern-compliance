"""Tests for OpenAI LLM service implementation."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from langchain_core.messages import AIMessage

from waivern_llm import BaseLLMService, LLMConfigurationError, OpenAILLMService

OPENAI_ENV_VARS = ["OPENAI_API_KEY", "OPENAI_MODEL"]


class TestOpenAILLMServiceInitialisation:
    """Test OpenAILLMService initialisation and configuration."""

    def test_initialisation_with_provided_parameters(self) -> None:
        """Test service initialisation with explicitly provided parameters."""
        service = OpenAILLMService(model_name="gpt-4", api_key="test-api-key")

        assert service.model_name == "gpt-4"
        # API key is private - service creation without error indicates it was set

    def test_initialisation_with_environment_variables(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test service initialisation using environment variables."""
        monkeypatch.setenv("OPENAI_MODEL", "gpt-3.5-turbo")
        monkeypatch.setenv("OPENAI_API_KEY", "env-api-key")

        service = OpenAILLMService()

        assert service.model_name == "gpt-3.5-turbo"
        # API key is private - service creation without error indicates it was set

    def test_initialisation_with_default_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test service initialisation uses default model when not specified."""
        for var in OPENAI_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        service = OpenAILLMService()

        assert service.model_name == "gpt-4o"
        # API key is private - service creation without error indicates it was set

    def test_initialisation_parameter_overrides_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that explicit parameters override environment variables."""
        monkeypatch.setenv("OPENAI_MODEL", "env-model")
        monkeypatch.setenv("OPENAI_API_KEY", "env-key")

        service = OpenAILLMService(model_name="param-model", api_key="param-key")

        assert service.model_name == "param-model"
        # API key is private - service creation without error indicates it was set

    def test_initialisation_missing_api_key_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that missing API key raises configuration error."""
        for var in OPENAI_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        with pytest.raises(LLMConfigurationError) as exc_info:
            OpenAILLMService()

        assert "OpenAI API key is required" in str(exc_info.value)
        assert "OPENAI_API_KEY" in str(exc_info.value)

    def test_initialisation_empty_api_key_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that empty API key raises configuration error."""
        monkeypatch.setenv("OPENAI_API_KEY", "")

        with pytest.raises(LLMConfigurationError) as exc_info:
            OpenAILLMService()

        assert "OpenAI API key is required" in str(exc_info.value)


class TestOpenAILLMServiceInvoke:
    """Test OpenAILLMService invoke functionality."""

    @pytest.fixture
    def service_with_mock_api(self) -> OpenAILLMService:
        """Create service instance with mocked API for testing."""
        return OpenAILLMService(model_name="gpt-4", api_key="test-api-key")

    def test_successful_invoke(self, service_with_mock_api: OpenAILLMService) -> None:
        """Test successful LLM invocation returns expected result."""
        prompt = "Identify personal data in: John Smith lives at 123 Main Street"
        expected_response = (
            "Personal data found: Name (John Smith), Address (123 Main Street)"
        )

        mock_response = AIMessage(content=expected_response)

        # Create mock ChatOpenAI class
        mock_chat_class = Mock()
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_chat_class.return_value = mock_llm

        # Mock the lazy import by patching __import__
        with patch.dict(
            "sys.modules", {"langchain_openai": Mock(ChatOpenAI=mock_chat_class)}
        ):
            result = service_with_mock_api.invoke(prompt)

            assert result == expected_response
            assert isinstance(result, str)

            # Verify the LLM was called with the prompt
            mock_llm.invoke.assert_called_once_with(prompt)

    def test_invoke_with_complex_response_content(
        self, service_with_mock_api: OpenAILLMService
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

        # Create mock ChatOpenAI class
        mock_chat_class = Mock()
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_chat_class.return_value = mock_llm

        # Mock the lazy import by patching sys.modules
        with patch.dict(
            "sys.modules", {"langchain_openai": Mock(ChatOpenAI=mock_chat_class)}
        ):
            result = service_with_mock_api.invoke(prompt)

            assert "Analysis result:" in result
            assert "Complex content structure" in result
            assert isinstance(result, str)


class TestOpenAILLMServiceBasics:
    """Test OpenAI LLM service basic functionality."""

    def test_openai_service_implements_base_interface(self) -> None:
        """Test that OpenAILLMService correctly implements BaseLLMService."""
        service = OpenAILLMService(model_name="gpt-4", api_key="test-key")

        assert isinstance(service, BaseLLMService)
        assert hasattr(service, "invoke")
        assert callable(service.invoke)
