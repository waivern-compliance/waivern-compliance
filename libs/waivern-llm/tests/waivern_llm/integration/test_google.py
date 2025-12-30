"""Integration tests with real Google Gemini API.

These tests require GOOGLE_API_KEY and langchain-google-genai package.
Run with: uv run pytest -m integration
"""

from __future__ import annotations

import os

import pytest

from waivern_llm import GoogleLLMService


class TestGoogleLLMServiceIntegration:
    """Integration tests with real Google Gemini API."""

    @pytest.mark.integration
    def test_simple_analysis(self, require_google: str) -> None:
        """Test real Google API with simple text analysis."""
        service = GoogleLLMService(api_key=require_google)

        text = "John Smith, email: john@example.com, phone: 555-1234"
        prompt = "List any personal data found in this text in a single line."

        result = service.analyse_data(text, prompt)

        # Verify response structure (don't assert exact content - LLM responses vary)
        assert isinstance(result, str)
        assert len(result) > 0
        # Check that response mentions some of the personal data
        assert "john" in result.lower() or "email" in result.lower()

    @pytest.mark.integration
    def test_default_model_from_environment(self, require_google: str) -> None:
        """Test real Google API uses default model from environment."""
        service = GoogleLLMService(api_key=require_google)

        # Verify model name is set (either default or from GOOGLE_MODEL env var)
        expected_default = "gemini-2.5-flash"
        env_model = os.getenv("GOOGLE_MODEL")
        expected_model = env_model if env_model else expected_default
        assert service.model_name == expected_model

        # Make a real API call to verify it works
        text = "Test data"
        prompt = "Reply with 'OK' if you can read this."

        result = service.analyse_data(text, prompt)

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.integration
    def test_custom_model(self, require_google: str) -> None:
        """Test real Google API with explicitly specified model."""
        custom_model = "gemini-2.5-flash-lite"
        service = GoogleLLMService(model_name=custom_model, api_key=require_google)

        assert service.model_name == custom_model

        # Make a real API call to verify it works with this model
        text = "Hello"
        prompt = "Reply with just the word 'Hi'"

        result = service.analyse_data(text, prompt)

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.integration
    def test_handles_empty_input(self, require_google: str) -> None:
        """Test real Google API handles edge cases gracefully."""
        service = GoogleLLMService(api_key=require_google)

        text = ""
        prompt = "If the text is empty, respond with just 'EMPTY'"

        result = service.analyse_data(text, prompt)

        # Even with empty input, we should get a valid response
        assert isinstance(result, str)
        assert len(result) > 0
        # LLM should recognise empty input
        assert "empty" in result.lower()
