"""Integration tests with real OpenAI API.

These tests require OPENAI_API_KEY and langchain-openai package.
Run with: uv run pytest -m integration
"""

from __future__ import annotations

import os

import pytest

from waivern_llm import OpenAILLMService


class TestOpenAILLMServiceIntegration:
    """Integration tests with real OpenAI API."""

    @pytest.mark.integration
    def test_simple_analysis(self, require_openai: str) -> None:
        """Test real OpenAI API with simple text analysis."""
        service = OpenAILLMService(api_key=require_openai)

        text = "John Smith, email: john@example.com, phone: 555-1234"
        prompt = "List any personal data found in this text in a single line."

        result = service.analyse_data(text, prompt)

        # Verify response structure (don't assert exact content - LLM responses vary)
        assert isinstance(result, str)
        assert len(result) > 0
        # Check that response mentions some of the personal data
        assert "john" in result.lower() or "email" in result.lower()

    @pytest.mark.integration
    def test_default_model_from_environment(self, require_openai: str) -> None:
        """Test real OpenAI API uses default model from environment."""
        service = OpenAILLMService(api_key=require_openai)

        # Verify model name is set (either default or from OPENAI_MODEL env var)
        expected_default = "gpt-4o"
        env_model = os.getenv("OPENAI_MODEL")
        expected_model = env_model if env_model else expected_default
        assert service.model_name == expected_model

        # Make a real API call to verify it works
        text = "Test data"
        prompt = "Reply with 'OK' if you can read this."

        result = service.analyse_data(text, prompt)

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.integration
    def test_custom_model(self, require_openai: str) -> None:
        """Test real OpenAI API with explicitly specified model."""
        custom_model = "gpt-4o-mini"
        service = OpenAILLMService(model_name=custom_model, api_key=require_openai)

        assert service.model_name == custom_model

        # Make a real API call to verify it works with this model
        text = "Hello"
        prompt = "Reply with just the word 'Hi'"

        result = service.analyse_data(text, prompt)

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.integration
    def test_handles_empty_input(self, require_openai: str) -> None:
        """Test real OpenAI API handles edge cases gracefully."""
        service = OpenAILLMService(api_key=require_openai)

        text = ""
        prompt = "If the text is empty, respond with just 'EMPTY'"

        result = service.analyse_data(text, prompt)

        # Even with empty input, we should get a valid response
        assert isinstance(result, str)
        assert len(result) > 0
        # LLM should recognise empty input
        assert "empty" in result.lower()
