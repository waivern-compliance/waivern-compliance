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


class TestOpenAILLMServiceDataAnalysis:
    """Test OpenAILLMService data analysis functionality."""

    @pytest.fixture
    def service_with_mock_api(self) -> OpenAILLMService:
        """Create service instance with mocked API for testing."""
        return OpenAILLMService(model_name="gpt-4", api_key="test-api-key")

    def test_successful_data_analysis(
        self, service_with_mock_api: OpenAILLMService
    ) -> None:
        """Test successful data analysis returns expected result."""
        text_to_analyse = "John Smith lives at 123 Main Street"
        analysis_prompt = "Identify personal data in the following text:"
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
            result = service_with_mock_api.analyse_data(
                text_to_analyse, analysis_prompt
            )

            assert result == expected_response
            assert isinstance(result, str)

            # Verify the LLM was called with the combined prompt
            mock_llm.invoke.assert_called_once()
            call_args = mock_llm.invoke.call_args[0][0]
            assert analysis_prompt in call_args
            assert text_to_analyse in call_args

    def test_data_analysis_with_complex_response_content(
        self, service_with_mock_api: OpenAILLMService
    ) -> None:
        """Test data analysis handles complex response content structures."""
        text_to_analyse = "Sample text for analysis"
        analysis_prompt = "Analyse this text:"

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
            result = service_with_mock_api.analyse_data(
                text_to_analyse, analysis_prompt
            )

            assert "Analysis result:" in result
            assert "Complex content structure" in result
            assert isinstance(result, str)


class TestOpenAILLMServiceBasics:
    """Test OpenAI LLM service basic functionality."""

    def test_openai_service_implements_base_interface(self) -> None:
        """Test that OpenAILLMService correctly implements BaseLLMService."""
        service = OpenAILLMService(model_name="gpt-4", api_key="test-key")

        assert isinstance(service, BaseLLMService)
        assert hasattr(service, "analyse_data")
        assert callable(service.analyse_data)
