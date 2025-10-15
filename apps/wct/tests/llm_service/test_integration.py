"""Integration tests with real LLM APIs.

These tests require actual API keys and make real API calls.
Run with: uv run pytest -m integration
"""

from __future__ import annotations

import os

import pytest

from wct.llm_service import AnthropicLLMService, GoogleLLMService, OpenAILLMService


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


class TestGoogleLLMServiceRealApiIntegration:
    """Integration tests with real Google API (requires GOOGLE_API_KEY and langchain-google-genai)."""

    @pytest.mark.integration
    def test_real_google_api_simple_analysis(self) -> None:
        """Test real Google API with simple text analysis."""
        # Skip if no API key
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            pytest.skip("GOOGLE_API_KEY not set - skipping real API test")

        # Skip if langchain-google-genai not installed
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI  # noqa: F401
        except ImportError:
            pytest.skip(
                "langchain-google-genai not installed - run: uv sync --group llm-google"
            )

        # Create real service (no mocks)
        service = GoogleLLMService(api_key=api_key)

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
    def test_real_google_api_with_default_model(self) -> None:
        """Test real Google API uses default model from environment."""
        # Skip if no API key
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            pytest.skip("GOOGLE_API_KEY not set - skipping real API test")

        # Skip if langchain-google-genai not installed
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI  # noqa: F401
        except ImportError:
            pytest.skip(
                "langchain-google-genai not installed - run: uv sync --group llm-google"
            )

        # Create service without specifying model (should use default or env var)
        service = GoogleLLMService(api_key=api_key)

        # Verify model name is set (either default or from GOOGLE_MODEL env var)
        expected_default = "gemini-2.5-flash"
        env_model = os.getenv("GOOGLE_MODEL")
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
    def test_real_google_api_with_custom_model(self) -> None:
        """Test real Google API with explicitly specified model."""
        # Skip if no API key
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            pytest.skip("GOOGLE_API_KEY not set - skipping real API test")

        # Skip if langchain-google-genai not installed
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI  # noqa: F401
        except ImportError:
            pytest.skip(
                "langchain-google-genai not installed - run: uv sync --group llm-google"
            )

        # Create service with explicitly specified model
        custom_model = "gemini-2.5-flash-lite"
        service = GoogleLLMService(model_name=custom_model, api_key=api_key)

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
    def test_real_google_api_handles_empty_response(self) -> None:
        """Test real Google API handles edge cases gracefully."""
        # Skip if no API key
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            pytest.skip("GOOGLE_API_KEY not set - skipping real API test")

        # Skip if langchain-google-genai not installed
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI  # noqa: F401
        except ImportError:
            pytest.skip(
                "langchain-google-genai not installed - run: uv sync --group llm-google"
            )

        # Create service
        service = GoogleLLMService(api_key=api_key)

        # Test with minimal input that might produce a brief response
        text = ""
        prompt = "If the text is empty, respond with just 'EMPTY'"

        result = service.analyse_data(text, prompt)

        # Even with empty input, we should get a valid response
        assert isinstance(result, str)
        assert len(result) > 0
        # LLM should recognize empty input
        assert "empty" in result.lower()
