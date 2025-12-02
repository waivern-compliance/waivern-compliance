"""Integration tests for LLM DI flow.

Tests the complete integration of ServiceContainer, LLMServiceFactory,
LLMServiceProvider, and LLMServiceConfiguration working together.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from waivern_core.services import ServiceContainer, ServiceDescriptor

from waivern_llm.base import BaseLLMService
from waivern_llm.di import (
    LLMServiceConfiguration,
    LLMServiceFactory,
    LLMServiceProvider,
)


class TestLLMDIIntegration:
    """Integration tests for the complete LLM DI system."""

    @staticmethod
    def create_container_with_factory(
        factory: LLMServiceFactory,
    ) -> ServiceContainer:
        """Helper to create container and register LLM factory as singleton."""
        container = ServiceContainer()
        container.register(ServiceDescriptor(BaseLLMService, factory, "singleton"))
        return container

    def test_full_di_flow_with_explicit_configuration(self) -> None:
        """Test complete DI flow: config → factory → container → service retrieval."""
        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "sk-test-key", "LLM_PROVIDER": "anthropic"},
            clear=True,
        ):
            config = LLMServiceConfiguration(
                provider="anthropic",
                api_key="sk-explicit-test-key",
                model="claude-3-opus",
            )
            factory = LLMServiceFactory(config)
            container = self.create_container_with_factory(factory)

            service = container.get_service(BaseLLMService)

            assert service is not None
            assert isinstance(service, BaseLLMService)

    def test_provider_returns_none_instead_of_raising_when_service_unavailable(
        self,
    ) -> None:
        """Test provider provides exception-safe service retrieval (graceful degradation)."""
        with patch.dict(
            os.environ,
            {"LLM_PROVIDER": "anthropic"},  # Missing ANTHROPIC_API_KEY
            clear=True,
        ):
            factory = LLMServiceFactory()
            container = self.create_container_with_factory(factory)
            provider = LLMServiceProvider(container)

            service = provider.get_service(BaseLLMService)

            assert service is None
            assert not provider.is_available(BaseLLMService)

    def test_zero_config_flow_with_environment_variables_only(self) -> None:
        """Test complete DI flow with zero-config pattern (convention over configuration)."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "sk-openai-test-key",
                "OPENAI_MODEL": "gpt-4-turbo",
            },
            clear=True,
        ):
            factory = LLMServiceFactory()  # Zero-config
            container = self.create_container_with_factory(factory)

            service = container.get_service(BaseLLMService)

            assert service is not None
            assert isinstance(service, BaseLLMService)

    def test_singleton_lifetime_returns_same_instance_across_multiple_retrievals(
        self,
    ) -> None:
        """Test container singleton lifetime management with LLM service factory."""
        with patch.dict(
            os.environ,
            {"LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "sk-singleton-key"},
            clear=True,
        ):
            factory = LLMServiceFactory()
            container = self.create_container_with_factory(factory)

            service_first = container.get_service(BaseLLMService)
            service_second = container.get_service(BaseLLMService)

            assert service_first is not None
            assert service_second is not None
            assert service_first is service_second  # Same instance

    @pytest.mark.parametrize(
        "env_vars",
        [
            {"LLM_PROVIDER": "google"},  # Missing API key
            {"LLM_PROVIDER": "invalid_provider"},  # Invalid provider
        ],
    )
    def test_invalid_configuration_returns_none_through_full_flow(
        self,
        env_vars: dict[str, str],
    ) -> None:
        """Test error handling integration - invalid config results in graceful failure."""
        with patch.dict(os.environ, env_vars, clear=True):
            factory = LLMServiceFactory()

            assert not factory.can_create()
            assert factory.create() is None

    @pytest.mark.parametrize(
        ("env_vars", "expected_available"),
        [
            (
                {"LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "sk-test-key"},
                True,
            ),
            ({"LLM_PROVIDER": "openai"}, False),  # Missing API key
        ],
    )
    def test_provider_availability_checking_before_retrieval(
        self,
        env_vars: dict[str, str],
        expected_available: bool,
    ) -> None:
        """Test is_available() pattern for checking optional dependencies before use."""
        with patch.dict(os.environ, env_vars, clear=True):
            factory = LLMServiceFactory()
            container = self.create_container_with_factory(factory)
            provider = LLMServiceProvider(container)

            assert provider.is_available(BaseLLMService) == expected_available

            service = provider.get_service(BaseLLMService)
            if expected_available:
                assert service is not None
            else:
                assert service is None
