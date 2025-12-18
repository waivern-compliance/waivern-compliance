"""Integration tests for LLM DI flow.

Tests the complete integration of ServiceContainer, LLMServiceFactory,
LLMServiceProvider, and LLMServiceConfiguration working together.
"""

from __future__ import annotations

import pytest
from waivern_core.services import ServiceContainer, ServiceDescriptor

from waivern_llm.base import BaseLLMService
from waivern_llm.di import (
    LLMServiceConfiguration,
    LLMServiceFactory,
    LLMServiceProvider,
)

# All LLM-related env vars that might interfere with tests
LLM_ENV_VARS = [
    "LLM_PROVIDER",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_MODEL",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "GOOGLE_API_KEY",
    "GOOGLE_MODEL",
]


@pytest.fixture
def clean_llm_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Clear all LLM environment variables for test isolation."""
    for var in LLM_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


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

    def test_full_di_flow_with_explicit_configuration(
        self, clean_llm_env: pytest.MonkeyPatch
    ) -> None:
        """Test complete DI flow: config → factory → container → service retrieval."""
        clean_llm_env.setenv("ANTHROPIC_API_KEY", "sk-test-key")
        clean_llm_env.setenv("LLM_PROVIDER", "anthropic")

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
        self, clean_llm_env: pytest.MonkeyPatch
    ) -> None:
        """Test provider provides exception-safe service retrieval (graceful degradation)."""
        clean_llm_env.setenv("LLM_PROVIDER", "anthropic")
        # Missing ANTHROPIC_API_KEY

        factory = LLMServiceFactory()
        container = self.create_container_with_factory(factory)
        provider = LLMServiceProvider(container)

        service = provider.get_service(BaseLLMService)

        assert service is None
        assert not provider.is_available(BaseLLMService)

    def test_zero_config_flow_with_environment_variables_only(
        self, clean_llm_env: pytest.MonkeyPatch
    ) -> None:
        """Test complete DI flow with zero-config pattern (convention over configuration)."""
        clean_llm_env.setenv("LLM_PROVIDER", "openai")
        clean_llm_env.setenv("OPENAI_API_KEY", "sk-openai-test-key")
        clean_llm_env.setenv("OPENAI_MODEL", "gpt-4-turbo")

        factory = LLMServiceFactory()  # Zero-config
        container = self.create_container_with_factory(factory)

        service = container.get_service(BaseLLMService)

        assert service is not None
        assert isinstance(service, BaseLLMService)

    def test_singleton_lifetime_returns_same_instance_across_multiple_retrievals(
        self, clean_llm_env: pytest.MonkeyPatch
    ) -> None:
        """Test container singleton lifetime management with LLM service factory."""
        clean_llm_env.setenv("LLM_PROVIDER", "anthropic")
        clean_llm_env.setenv("ANTHROPIC_API_KEY", "sk-singleton-key")

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
        clean_llm_env: pytest.MonkeyPatch,
        env_vars: dict[str, str],
    ) -> None:
        """Test error handling integration - invalid config results in graceful failure."""
        for key, value in env_vars.items():
            clean_llm_env.setenv(key, value)

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
        clean_llm_env: pytest.MonkeyPatch,
        env_vars: dict[str, str],
        expected_available: bool,
    ) -> None:
        """Test is_available() pattern for checking optional dependencies before use."""
        for key, value in env_vars.items():
            clean_llm_env.setenv(key, value)

        factory = LLMServiceFactory()
        container = self.create_container_with_factory(factory)
        provider = LLMServiceProvider(container)

        assert provider.is_available(BaseLLMService) == expected_available

        service = provider.get_service(BaseLLMService)
        if expected_available:
            assert service is not None
        else:
            assert service is None
