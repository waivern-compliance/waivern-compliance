"""Tests for BaseLLMService abstract base class."""

from __future__ import annotations

from waivern_llm import AnthropicLLMService, BaseLLMService


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
