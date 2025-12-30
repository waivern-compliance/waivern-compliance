"""Integration tests with real Anthropic API.

These tests require ANTHROPIC_API_KEY and make real API calls.
Run with: uv run pytest -m integration
"""

from __future__ import annotations

import os

import pytest

from waivern_llm import AnthropicLLMService


class TestAnthropicLLMServiceIntegration:
    """Integration tests with real Anthropic API."""

    @pytest.mark.integration
    def test_simple_analysis(self, require_anthropic_api_key: str) -> None:
        """Test real Anthropic API with simple text analysis."""
        service = AnthropicLLMService(api_key=require_anthropic_api_key)

        text = "John Smith, email: john@example.com, phone: 555-1234"
        prompt = "List any personal data found in this text in a single line."

        result = service.analyse_data(text, prompt)

        # Verify response structure (don't assert exact content - LLM responses vary)
        assert isinstance(result, str)
        assert len(result) > 0
        # Check that response mentions some of the personal data
        assert "john" in result.lower() or "email" in result.lower()

    @pytest.mark.integration
    def test_default_model_from_environment(
        self, require_anthropic_api_key: str
    ) -> None:
        """Test real Anthropic API uses default model from environment."""
        service = AnthropicLLMService(api_key=require_anthropic_api_key)

        # Verify model name is set (either default or from ANTHROPIC_MODEL env var)
        expected_default = "claude-sonnet-4-5-20250929"
        env_model = os.getenv("ANTHROPIC_MODEL")
        expected_model = env_model if env_model else expected_default
        assert service.model_name == expected_model

        # Make a real API call to verify it works
        text = "Test data"
        prompt = "Reply with 'OK' if you can read this."

        result = service.analyse_data(text, prompt)

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.integration
    def test_custom_model(self, require_anthropic_api_key: str) -> None:
        """Test real Anthropic API with explicitly specified model."""
        custom_model = "claude-3-5-haiku-latest"
        service = AnthropicLLMService(
            model_name=custom_model, api_key=require_anthropic_api_key
        )

        assert service.model_name == custom_model

        # Make a real API call to verify it works with this model
        text = "Hello"
        prompt = "Reply with just the word 'Hi'"

        result = service.analyse_data(text, prompt)

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.integration
    def test_handles_empty_input(self, require_anthropic_api_key: str) -> None:
        """Test real Anthropic API handles edge cases gracefully."""
        service = AnthropicLLMService(api_key=require_anthropic_api_key)

        text = ""
        prompt = "If the text is empty, respond with just 'EMPTY'"

        result = service.analyse_data(text, prompt)

        # Even with empty input, we should get a valid response
        assert isinstance(result, str)
        assert len(result) > 0
        # LLM should recognise empty input
        assert "empty" in result.lower()
