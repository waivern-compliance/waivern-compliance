"""Tests for LLM DI service factory."""

from __future__ import annotations

import os
from unittest.mock import patch


class TestLLMServiceFactoryCanCreate:
    """Test LLMServiceFactory.can_create() validation logic."""

    def test_can_create_returns_true_for_valid_anthropic_config(self) -> None:
        """Test can_create() returns True when Anthropic configuration is valid."""
        from waivern_llm.di.factory import LLMServiceFactory

        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "anthropic",
                "ANTHROPIC_API_KEY": "test-anthropic-key",
            },
            clear=True,
        ):
            factory = LLMServiceFactory()
            result = factory.can_create()

            assert result is True

    def test_can_create_returns_true_for_valid_openai_config(self) -> None:
        """Test can_create() returns True when OpenAI configuration is valid."""
        from waivern_llm.di.factory import LLMServiceFactory

        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "test-openai-key",
            },
            clear=True,
        ):
            factory = LLMServiceFactory()
            result = factory.can_create()

            assert result is True

    def test_can_create_returns_true_for_valid_google_config(self) -> None:
        """Test can_create() returns True when Google configuration is valid."""
        from waivern_llm.di.factory import LLMServiceFactory

        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "google",
                "GOOGLE_API_KEY": "test-google-key",
            },
            clear=True,
        ):
            factory = LLMServiceFactory()
            result = factory.can_create()

            assert result is True

    def test_can_create_returns_false_when_api_key_missing(self) -> None:
        """Test can_create() returns False when required API key is not available."""
        from waivern_llm.di.factory import LLMServiceFactory

        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "anthropic",
                # No ANTHROPIC_API_KEY provided
            },
            clear=True,
        ):
            factory = LLMServiceFactory()
            result = factory.can_create()

            assert result is False

    def test_can_create_returns_false_for_invalid_provider(self) -> None:
        """Test can_create() returns False when LLM_PROVIDER is unsupported."""
        from waivern_llm.di.factory import LLMServiceFactory

        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "unsupported_provider",
                "UNSUPPORTED_API_KEY": "test-key",  # Even with key, invalid provider fails
            },
            clear=True,
        ):
            factory = LLMServiceFactory()
            result = factory.can_create()

            assert result is False


class TestLLMServiceFactoryCreate:
    """Test LLMServiceFactory.create() service creation logic."""

    def test_create_returns_service_for_valid_config(self) -> None:
        """Test create() returns BaseLLMService instance when configuration is valid."""
        from waivern_llm.base import BaseLLMService
        from waivern_llm.di.factory import LLMServiceFactory

        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "anthropic",
                "ANTHROPIC_API_KEY": "test-anthropic-key",
            },
            clear=True,
        ):
            factory = LLMServiceFactory()
            service = factory.create()

            assert service is not None
            assert isinstance(service, BaseLLMService)

    def test_create_returns_none_when_api_key_missing(self) -> None:
        """Test create() returns None instead of raising exception when API key missing."""
        from waivern_llm.di.factory import LLMServiceFactory

        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "anthropic",
                # No ANTHROPIC_API_KEY provided
            },
            clear=True,
        ):
            factory = LLMServiceFactory()
            service = factory.create()

            # Should return None, not raise exception (graceful degradation)
            assert service is None

    def test_create_returns_none_for_invalid_provider(self) -> None:
        """Test create() returns None when provider is invalid rather than raising exception."""
        from waivern_llm.di.factory import LLMServiceFactory

        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "unsupported_provider",
                "SOME_API_KEY": "test-key",
            },
            clear=True,
        ):
            factory = LLMServiceFactory()
            service = factory.create()

            # Should return None, not raise exception (graceful degradation)
            assert service is None
