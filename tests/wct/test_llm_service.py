"""Tests for LLM service implementation.

This module tests the public interface of the LLM service components,
focusing on black-box testing of behaviour and contracts without
accessing private implementation details. ✔️
"""

from __future__ import annotations

import os
from unittest.mock import Mock, patch

import pytest
from langchain_core.messages import AIMessage

from wct.llm_service import (
    AnthropicLLMService,
    BaseLLMService,
    LLMConfigurationError,
    LLMServiceFactory,
    OpenAILLMService,
)


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


class TestBaseLLMServiceAbstraction:
    """Test BaseLLMService abstract base class."""

    def test_anthropic_service_implements_base_interface(self) -> None:
        """Test that AnthropicLLMService correctly implements BaseLLMService."""
        service = AnthropicLLMService(
            model_name="claude-3-sonnet-20240229", api_key="test-key"
        )

        assert isinstance(service, BaseLLMService)
        assert hasattr(service, "analyse_data")
        assert callable(service.analyse_data)


class TestAnthropicLLMServiceIntegration:
    """Integration tests for AnthropicLLMService behaviour."""

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


class TestOpenAILLMServiceInitialisation:
    """Test OpenAILLMService initialisation and configuration."""

    def test_initialisation_with_provided_parameters(self) -> None:
        """Test service initialisation with explicitly provided parameters."""
        service = OpenAILLMService(model_name="gpt-4", api_key="test-api-key")

        assert service.model_name == "gpt-4"
        # API key is private - service creation without error indicates it was set

    def test_initialisation_with_environment_variables(self) -> None:
        """Test service initialisation using environment variables."""
        with patch.dict(
            os.environ,
            {
                "OPENAI_MODEL": "gpt-3.5-turbo",
                "OPENAI_API_KEY": "env-api-key",
            },
        ):
            service = OpenAILLMService()

            assert service.model_name == "gpt-3.5-turbo"
            # API key is private - service creation without error indicates it was set

    def test_initialisation_with_default_model(self) -> None:
        """Test service initialisation uses default model when not specified."""
        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "test-key"},
            clear=True,
        ):
            service = OpenAILLMService()

            assert service.model_name == "gpt-4o"
            # API key is private - service creation without error indicates it was set

    def test_initialisation_parameter_overrides_environment(self) -> None:
        """Test that explicit parameters override environment variables."""
        with patch.dict(
            os.environ,
            {
                "OPENAI_MODEL": "env-model",
                "OPENAI_API_KEY": "env-key",
            },
        ):
            service = OpenAILLMService(model_name="param-model", api_key="param-key")

            assert service.model_name == "param-model"
            # API key is private - service creation without error indicates it was set

    def test_initialisation_missing_api_key_raises_error(self) -> None:
        """Test that missing API key raises configuration error."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(LLMConfigurationError) as exc_info:
                OpenAILLMService()

            assert "OpenAI API key is required" in str(exc_info.value)
            assert "OPENAI_API_KEY" in str(exc_info.value)

    def test_initialisation_empty_api_key_raises_error(self) -> None:
        """Test that empty API key raises configuration error."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
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


class TestLLMServiceFactory:
    """Test LLM service factory methods."""

    def test_factory_can_create_openai_service(self) -> None:
        """Test that factory can create OpenAI service instance."""
        service = LLMServiceFactory.create_openai_service(
            model_name="gpt-4", api_key="test-key"
        )

        assert isinstance(service, OpenAILLMService)
        assert service.model_name == "gpt-4"


class TestAnthropicLLMServiceRealApiIntegration:
    """Integration tests with real Anthropic API (requires ANTHROPIC_API_KEY)."""

    @pytest.mark.integration
    def test_real_anthropic_api_simple_analysis(self) -> None:
        """Test real Anthropic API with simple text analysis."""
        # Skip if no API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("ANTHROPIC_API_KEY not set - skipping real API test")

        # Create real service (no mocks)
        service = AnthropicLLMService(api_key=api_key)

        # Simple test with clear expected content
        text = "John Smith, email: john@example.com, phone: 555-1234"
        prompt = "List any personal data found in this text in a single line."

        # Make real API call
        result = service.analyse_data(text, prompt)

        # Verify response structure (don't assert exact content - LLM responses vary)
        assert isinstance(result, str)
        assert len(result) > 0
        # Check that response mentions some of the personal data
        assert "john" in result.lower() or "email" in result.lower()

    @pytest.mark.integration
    def test_real_anthropic_api_with_default_model(self) -> None:
        """Test real Anthropic API uses default model from environment."""
        # Skip if no API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("ANTHROPIC_API_KEY not set - skipping real API test")

        # Create service without specifying model (should use default or env var)
        service = AnthropicLLMService(api_key=api_key)

        # Verify model name is set (either default or from ANTHROPIC_MODEL env var)
        expected_default = "claude-sonnet-4-5-20250929"
        env_model = os.getenv("ANTHROPIC_MODEL")
        expected_model = env_model if env_model else expected_default
        assert service.model_name == expected_model

        # Make a real API call to verify it works
        text = "Test data"
        prompt = "Reply with 'OK' if you can read this."

        result = service.analyse_data(text, prompt)

        # Verify we got a response
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.integration
    def test_real_anthropic_api_with_custom_model(self) -> None:
        """Test real Anthropic API with explicitly specified model."""
        # Skip if no API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("ANTHROPIC_API_KEY not set - skipping real API test")

        # Create service with explicitly specified model
        custom_model = "claude-3-5-sonnet-20241022"
        service = AnthropicLLMService(model_name=custom_model, api_key=api_key)

        # Verify the model name is set correctly
        assert service.model_name == custom_model

        # Make a real API call to verify it works with this model
        text = "Hello"
        prompt = "Reply with just the word 'Hi'"

        result = service.analyse_data(text, prompt)

        # Verify we got a response
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.integration
    def test_real_anthropic_api_handles_empty_response(self) -> None:
        """Test real Anthropic API handles edge cases gracefully."""
        # Skip if no API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("ANTHROPIC_API_KEY not set - skipping real API test")

        # Create service
        service = AnthropicLLMService(api_key=api_key)

        # Test with minimal input that might produce a brief response
        text = ""
        prompt = "If the text is empty, respond with just 'EMPTY'"

        result = service.analyse_data(text, prompt)

        # Even with empty input, we should get a valid response
        assert isinstance(result, str)
        assert len(result) > 0
        # LLM should recognize empty input
        assert "empty" in result.lower()


class TestOpenAILLMServiceRealApiIntegration:
    """Integration tests with real OpenAI API (requires OPENAI_API_KEY and langchain-openai)."""

    @pytest.mark.integration
    def test_real_openai_api_simple_analysis(self) -> None:
        """Test real OpenAI API with simple text analysis."""
        # Skip if no API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            pytest.skip("OPENAI_API_KEY not set - skipping real API test")

        # Skip if langchain-openai not installed
        try:
            from langchain_openai import ChatOpenAI  # noqa: F401
        except ImportError:
            pytest.skip(
                "langchain-openai not installed - run: uv sync --group llm-openai"
            )

        # Create real service (no mocks)
        service = OpenAILLMService(api_key=api_key)

        # Simple test with clear expected content
        text = "John Smith, email: john@example.com, phone: 555-1234"
        prompt = "List any personal data found in this text in a single line."

        # Make real API call
        result = service.analyse_data(text, prompt)

        # Verify response structure (don't assert exact content - LLM responses vary)
        assert isinstance(result, str)
        assert len(result) > 0
        # Check that response mentions some of the personal data
        assert "john" in result.lower() or "email" in result.lower()

    @pytest.mark.integration
    def test_real_openai_api_with_default_model(self) -> None:
        """Test real OpenAI API uses default model from environment."""
        # Skip if no API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            pytest.skip("OPENAI_API_KEY not set - skipping real API test")

        # Skip if langchain-openai not installed
        try:
            from langchain_openai import ChatOpenAI  # noqa: F401
        except ImportError:
            pytest.skip(
                "langchain-openai not installed - run: uv sync --group llm-openai"
            )

        # Create service without specifying model (should use default or env var)
        service = OpenAILLMService(api_key=api_key)

        # Verify model name is set (either default or from OPENAI_MODEL env var)
        expected_default = "gpt-4o"
        env_model = os.getenv("OPENAI_MODEL")
        expected_model = env_model if env_model else expected_default
        assert service.model_name == expected_model

        # Make a real API call to verify it works
        text = "Test data"
        prompt = "Reply with 'OK' if you can read this."

        result = service.analyse_data(text, prompt)

        # Verify we got a response
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.integration
    def test_real_openai_api_with_custom_model(self) -> None:
        """Test real OpenAI API with explicitly specified model."""
        # Skip if no API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            pytest.skip("OPENAI_API_KEY not set - skipping real API test")

        # Skip if langchain-openai not installed
        try:
            from langchain_openai import ChatOpenAI  # noqa: F401
        except ImportError:
            pytest.skip(
                "langchain-openai not installed - run: uv sync --group llm-openai"
            )

        # Create service with explicitly specified model
        custom_model = "gpt-4o-mini"
        service = OpenAILLMService(model_name=custom_model, api_key=api_key)

        # Verify the model name is set correctly
        assert service.model_name == custom_model

        # Make a real API call to verify it works with this model
        text = "Hello"
        prompt = "Reply with just the word 'Hi'"

        result = service.analyse_data(text, prompt)

        # Verify we got a response
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.integration
    def test_real_openai_api_handles_empty_response(self) -> None:
        """Test real OpenAI API handles edge cases gracefully."""
        # Skip if no API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            pytest.skip("OPENAI_API_KEY not set - skipping real API test")

        # Skip if langchain-openai not installed
        try:
            from langchain_openai import ChatOpenAI  # noqa: F401
        except ImportError:
            pytest.skip(
                "langchain-openai not installed - run: uv sync --group llm-openai"
            )

        # Create service
        service = OpenAILLMService(api_key=api_key)

        # Test with minimal input that might produce a brief response
        text = ""
        prompt = "If the text is empty, respond with just 'EMPTY'"

        result = service.analyse_data(text, prompt)

        # Even with empty input, we should get a valid response
        assert isinstance(result, str)
        assert len(result) > 0
        # LLM should recognize empty input
        assert "empty" in result.lower()
