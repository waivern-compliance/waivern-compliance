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
    def test_simple_invoke(self, require_google: str) -> None:
        """Test real Google API with simple invocation."""
        service = GoogleLLMService(api_key=require_google)

        prompt = (
            "List any personal data found in this text in a single line: "
            "John Smith, email: john@example.com, phone: 555-1234"
        )

        result = service.invoke(prompt)

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
        prompt = "Reply with 'OK' if you can read this."

        result = service.invoke(prompt)

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.integration
    def test_custom_model(self, require_google: str) -> None:
        """Test real Google API with explicitly specified model."""
        custom_model = "gemini-2.5-flash-lite"
        service = GoogleLLMService(model_name=custom_model, api_key=require_google)

        assert service.model_name == custom_model

        # Make a real API call to verify it works with this model
        prompt = "Reply with just the word 'Hi'"

        result = service.invoke(prompt)

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.integration
    def test_handles_empty_prompt(self, require_google: str) -> None:
        """Test real Google API handles edge cases gracefully."""
        service = GoogleLLMService(api_key=require_google)

        prompt = "The following text is empty: ''. Respond with just 'EMPTY'"

        result = service.invoke(prompt)

        # Even with empty text, we should get a valid response
        assert isinstance(result, str)
        assert len(result) > 0
        # LLM should recognise empty input
        assert "empty" in result.lower()
