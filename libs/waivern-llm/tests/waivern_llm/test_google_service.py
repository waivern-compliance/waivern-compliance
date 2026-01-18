"""Tests for Google LLM service implementation."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from langchain_core.messages import AIMessage

from waivern_llm import BaseLLMService, GoogleLLMService, LLMConfigurationError

GOOGLE_ENV_VARS = ["GOOGLE_API_KEY", "GOOGLE_MODEL"]


class TestGoogleLLMServiceInitialisation:
    """Test GoogleLLMService initialisation and configuration."""

    def test_initialisation_with_provided_parameters(self) -> None:
        """Test service initialisation with explicitly provided parameters."""
        service = GoogleLLMService(model_name="gemini-1.5-pro", api_key="test-api-key")

        assert service.model_name == "gemini-1.5-pro"
        # API key is private - service creation without error indicates it was set

    def test_initialisation_with_environment_variables(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test service initialisation using environment variables."""
        monkeypatch.setenv("GOOGLE_MODEL", "gemini-1.5-flash")
        monkeypatch.setenv("GOOGLE_API_KEY", "env-api-key")

        service = GoogleLLMService()

        assert service.model_name == "gemini-1.5-flash"
        # API key is private - service creation without error indicates it was set

    def test_initialisation_with_default_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test service initialisation uses default model when not specified."""
        for var in GOOGLE_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

        service = GoogleLLMService()

        assert service.model_name == "gemini-2.5-flash"
        # API key is private - service creation without error indicates it was set

    def test_initialisation_parameter_overrides_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that explicit parameters override environment variables."""
        monkeypatch.setenv("GOOGLE_MODEL", "env-model")
        monkeypatch.setenv("GOOGLE_API_KEY", "env-key")

        service = GoogleLLMService(model_name="param-model", api_key="param-key")

        assert service.model_name == "param-model"
        # API key is private - service creation without error indicates it was set

    def test_initialisation_missing_api_key_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that missing API key raises configuration error."""
        for var in GOOGLE_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        with pytest.raises(LLMConfigurationError) as exc_info:
            GoogleLLMService()

        assert "Google API key is required" in str(exc_info.value)
        assert "GOOGLE_API_KEY" in str(exc_info.value)

    def test_initialisation_empty_api_key_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that empty API key raises configuration error."""
        monkeypatch.setenv("GOOGLE_API_KEY", "")

        with pytest.raises(LLMConfigurationError) as exc_info:
            GoogleLLMService()

        assert "Google API key is required" in str(exc_info.value)

    def test_google_service_implements_base_interface(self) -> None:
        """Test that GoogleLLMService correctly implements BaseLLMService."""
        service = GoogleLLMService(model_name="gemini-1.5-pro", api_key="test-key")

        assert isinstance(service, BaseLLMService)
        assert hasattr(service, "invoke")
        assert callable(service.invoke)


class TestGoogleLLMServiceInvoke:
    """Test GoogleLLMService invoke functionality."""

    @pytest.fixture
    def service_with_mock_api(self) -> GoogleLLMService:
        """Create service instance with mocked API for testing."""
        return GoogleLLMService(model_name="gemini-1.5-pro", api_key="test-api-key")

    def test_successful_invoke(self, service_with_mock_api: GoogleLLMService) -> None:
        """Test successful LLM invocation returns expected result."""
        prompt = "Identify personal data in: John Smith lives at 123 Main Street"
        expected_response = (
            "Personal data found: Name (John Smith), Address (123 Main Street)"
        )

        mock_response = AIMessage(content=expected_response)

        # Create mock ChatGoogleGenerativeAI class
        mock_chat_class = Mock()
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_chat_class.return_value = mock_llm

        # Mock the lazy import by patching sys.modules
        with patch.dict(
            "sys.modules",
            {"langchain_google_genai": Mock(ChatGoogleGenerativeAI=mock_chat_class)},
        ):
            result = service_with_mock_api.invoke(prompt)

            assert result == expected_response
            assert isinstance(result, str)

            # Verify the LLM was called with the prompt
            mock_llm.invoke.assert_called_once_with(prompt)

    def test_invoke_with_complex_response_content(
        self, service_with_mock_api: GoogleLLMService
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

        # Create mock ChatGoogleGenerativeAI class
        mock_chat_class = Mock()
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_chat_class.return_value = mock_llm

        # Mock the lazy import by patching sys.modules
        with patch.dict(
            "sys.modules",
            {"langchain_google_genai": Mock(ChatGoogleGenerativeAI=mock_chat_class)},
        ):
            result = service_with_mock_api.invoke(prompt)

            assert "Analysis result:" in result
            assert "Complex content structure" in result
            assert isinstance(result, str)
