"""Tests for Anthropic LLM service implementation."""

from __future__ import annotations

import os
from unittest.mock import Mock, patch

import pytest
from langchain_core.messages import AIMessage

from wct.llm_service import AnthropicLLMService, LLMConfigurationError


class TestAnthropicLLMServiceInitialisation:
    """Test AnthropicLLMService initialisation and configuration."""

    def test_initialisation_with_provided_parameters(self) -> None:
        """Test service initialisation with explicitly provided parameters."""
        service = AnthropicLLMService(
            model_name="claude-3-sonnet-20240229", api_key="test-api-key"
        )

        assert service.model_name == "claude-3-sonnet-20240229"
        # API key is private - service creation without error indicates it was set

    def test_initialisation_with_environment_variables(self) -> None:
        """Test service initialisation using environment variables."""
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_MODEL": "claude-3-opus-20240229",
                "ANTHROPIC_API_KEY": "env-api-key",
            },
        ):
            service = AnthropicLLMService()

            assert service.model_name == "claude-3-opus-20240229"
            # API key is private - service creation without error indicates it was set

    def test_initialisation_with_default_model(self) -> None:
        """Test service initialisation uses default model when not specified."""
        # Clear both ANTHROPIC_MODEL and set ANTHROPIC_API_KEY to ensure default is used
        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "test-key"},
            clear=True,  # Clear all env vars to ensure no ANTHROPIC_MODEL is present
        ):
            service = AnthropicLLMService()

            assert service.model_name == "claude-sonnet-4-5-20250929"
            # API key is private - service creation without error indicates it was set

    def test_initialisation_parameter_overrides_environment(self) -> None:
        """Test that explicit parameters override environment variables."""
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_MODEL": "env-model",
                "ANTHROPIC_API_KEY": "env-key",
            },
        ):
            service = AnthropicLLMService(model_name="param-model", api_key="param-key")

            assert service.model_name == "param-model"
            # API key is private - service creation without error indicates it was set

    def test_initialisation_missing_api_key_raises_error(self) -> None:
        """Test that missing API key raises configuration error."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(LLMConfigurationError) as exc_info:
                AnthropicLLMService()

            assert "Anthropic API key is required" in str(exc_info.value)
            assert "ANTHROPIC_API_KEY" in str(exc_info.value)

    def test_initialisation_empty_api_key_raises_error(self) -> None:
        """Test that empty API key raises configuration error."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            with pytest.raises(LLMConfigurationError) as exc_info:
                AnthropicLLMService()

            assert "Anthropic API key is required" in str(exc_info.value)


class TestAnthropicLLMServiceDataAnalysis:
    """Test AnthropicLLMService data analysis functionality."""

    @pytest.fixture
    def service_with_mock_api(self) -> AnthropicLLMService:
        """Create service instance with mocked API for testing."""
        return AnthropicLLMService(
            model_name="claude-3-sonnet-20240229", api_key="test-api-key"
        )

    def test_successful_data_analysis(
        self, service_with_mock_api: AnthropicLLMService
    ) -> None:
        """Test successful data analysis returns expected result."""
        text_to_analyse = "John Smith lives at 123 Main Street"
        analysis_prompt = "Identify personal data in the following text:"
        expected_response = (
            "Personal data found: Name (John Smith), Address (123 Main Street)"
        )

        mock_response = AIMessage(content=expected_response)

        with patch("wct.llm_service.ChatAnthropic") as mock_chat:
            mock_llm = Mock()
            mock_llm.invoke.return_value = mock_response
            mock_chat.return_value = mock_llm

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
        self, service_with_mock_api: AnthropicLLMService
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

        with patch("wct.llm_service.ChatAnthropic") as mock_chat:
            mock_llm = Mock()
            mock_llm.invoke.return_value = mock_response
            mock_chat.return_value = mock_llm

            result = service_with_mock_api.analyse_data(
                text_to_analyse, analysis_prompt
            )

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

        with patch("wct.llm_service.ChatAnthropic") as mock_chat:
            mock_llm = Mock()
            mock_llm.invoke.side_effect = [mock_response1, mock_response2]
            mock_chat.return_value = mock_llm

            # First operation
            result1 = service.analyse_data("text1", "prompt1")
            assert result1 == "First response"

            # Second operation
            result2 = service.analyse_data("text2", "prompt2")
            assert result2 == "Second response"

            # Verify both calls were made
            assert mock_llm.invoke.call_count == 2
