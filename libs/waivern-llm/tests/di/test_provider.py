"""Tests for LLM DI service provider."""

from __future__ import annotations

import os
from unittest.mock import patch

from waivern_core.services import ServiceContainer, ServiceDescriptor

from waivern_llm.base import BaseLLMService
from waivern_llm.di.factory import LLMServiceFactory
from waivern_llm.di.provider import LLMServiceProvider


class TestLLMServiceProvider:
    """Test LLMServiceProvider protocol implementation."""

    def test_provider_can_be_instantiated_with_container(self) -> None:
        """Test provider can be instantiated with a ServiceContainer."""
        container = ServiceContainer()
        provider = LLMServiceProvider(container)

        assert provider is not None

    def test_get_service_returns_service_when_available(self) -> None:
        """Test get_service() returns service instance when registered and available."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "anthropic",
                "ANTHROPIC_API_KEY": "test-key",
            },
            clear=True,
        ):
            container = ServiceContainer()
            container.register(
                ServiceDescriptor(BaseLLMService, LLMServiceFactory(), "singleton")
            )

            provider = LLMServiceProvider(container)
            service = provider.get_service(BaseLLMService)

            assert service is not None
            assert isinstance(service, BaseLLMService)

    def test_get_service_returns_none_when_service_unavailable(self) -> None:
        """Test get_service() returns None when service factory returns None."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "anthropic",
                # No ANTHROPIC_API_KEY - factory will return None
            },
            clear=True,
        ):
            container = ServiceContainer()
            container.register(
                ServiceDescriptor(BaseLLMService, LLMServiceFactory(), "singleton")
            )

            provider = LLMServiceProvider(container)
            service = provider.get_service(BaseLLMService)

            # Should return None, not raise ValueError
            assert service is None

    def test_get_service_returns_none_when_service_not_registered(self) -> None:
        """Test get_service() returns None when service type not registered."""
        container = ServiceContainer()
        # No service registered

        provider = LLMServiceProvider(container)
        service = provider.get_service(BaseLLMService)

        # Should return None, not raise KeyError
        assert service is None

    def test_is_available_returns_true_when_service_can_be_retrieved(self) -> None:
        """Test is_available() returns True when service is available."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "anthropic",
                "ANTHROPIC_API_KEY": "test-key",
            },
            clear=True,
        ):
            container = ServiceContainer()
            container.register(
                ServiceDescriptor(BaseLLMService, LLMServiceFactory(), "singleton")
            )

            provider = LLMServiceProvider(container)
            result = provider.is_available(BaseLLMService)

            assert result is True

    def test_is_available_returns_false_when_service_unavailable(self) -> None:
        """Test is_available() returns False when service cannot be created."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "anthropic",
                # No ANTHROPIC_API_KEY - service unavailable
            },
            clear=True,
        ):
            container = ServiceContainer()
            container.register(
                ServiceDescriptor(BaseLLMService, LLMServiceFactory(), "singleton")
            )

            provider = LLMServiceProvider(container)
            result = provider.is_available(BaseLLMService)

            assert result is False
