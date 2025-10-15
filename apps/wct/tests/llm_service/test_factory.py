"""Tests for LLM service factory."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from wct.llm_service import (
    AnthropicLLMService,
    GoogleLLMService,
    LLMConfigurationError,
    LLMServiceFactory,
    OpenAILLMService,
)


class TestLLMServiceFactory:
    """Test LLM service factory methods."""

    def test_factory_can_create_openai_service(self) -> None:
        """Test that factory can create OpenAI service instance."""
        service = LLMServiceFactory.create_openai_service(
            model_name="gpt-4", api_key="test-key"
        )

        assert isinstance(service, OpenAILLMService)
        assert service.model_name == "gpt-4"

    def test_factory_can_create_google_service(self) -> None:
        """Test that factory can create Google service instance."""
        service = LLMServiceFactory.create_google_service(
            model_name="gemini-1.5-pro", api_key="test-key"
        )

        assert isinstance(service, GoogleLLMService)
        assert service.model_name == "gemini-1.5-pro"


class TestLLMServiceFactoryProviderSelection:
    """Test LLM service factory provider selection via LLM_PROVIDER environment variable."""

    def test_create_service_with_anthropic_provider(self) -> None:
        """Test create_service() creates Anthropic service when LLM_PROVIDER=anthropic."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "anthropic",
                "ANTHROPIC_API_KEY": "test-key",
            },
        ):
            service = LLMServiceFactory.create_service()

            assert isinstance(service, AnthropicLLMService)

    def test_create_service_with_openai_provider(self) -> None:
        """Test create_service() creates OpenAI service when LLM_PROVIDER=openai."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "test-key",
            },
        ):
            service = LLMServiceFactory.create_service()

            assert isinstance(service, OpenAILLMService)

    def test_create_service_with_google_provider(self) -> None:
        """Test create_service() creates Google service when LLM_PROVIDER=google."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "google",
                "GOOGLE_API_KEY": "test-key",
            },
        ):
            service = LLMServiceFactory.create_service()

            assert isinstance(service, GoogleLLMService)

    def test_create_service_defaults_to_anthropic_when_no_provider_set(self) -> None:
        """Test create_service() defaults to Anthropic when LLM_PROVIDER not set."""
        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "test-key"},
            clear=True,
        ):
            service = LLMServiceFactory.create_service()

            assert isinstance(service, AnthropicLLMService)

    def test_create_service_with_invalid_provider_raises_error(self) -> None:
        """Test create_service() raises error for invalid provider."""
        with patch.dict(
            os.environ,
            {"LLM_PROVIDER": "invalid-provider"},
        ):
            with pytest.raises(LLMConfigurationError) as exc_info:
                LLMServiceFactory.create_service()

            assert "invalid-provider" in str(exc_info.value).lower()
            assert "anthropic" in str(exc_info.value).lower()
            assert "openai" in str(exc_info.value).lower()
            assert "google" in str(exc_info.value).lower()
