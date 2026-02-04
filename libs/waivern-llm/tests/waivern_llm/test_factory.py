"""Tests for LLMServiceFactory.

Business behaviour: Creates LLMService instances with the correct provider
and cache store, resolving dependencies lazily from the ServiceContainer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

from waivern_artifact_store.base import ArtifactStore
from waivern_core.services import ServiceContainer, ServiceDescriptor

from waivern_llm.di.configuration import LLMServiceConfiguration
from waivern_llm.factory import LLMServiceFactory

if TYPE_CHECKING:
    import pytest

# Environment variables to clear for isolated tests
ENV_VARS_TO_CLEAR = [
    "LLM_PROVIDER",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_MODEL",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "OPENAI_BASE_URL",
    "GOOGLE_API_KEY",
    "GOOGLE_MODEL",
]


def _create_mock_container() -> ServiceContainer:
    """Create a ServiceContainer with a mock ArtifactStore registered."""
    container = ServiceContainer()

    # Create a mock factory that returns a mock ArtifactStore
    mock_store = Mock(spec=ArtifactStore)
    mock_factory = Mock()
    mock_factory.create.return_value = mock_store
    mock_factory.can_create.return_value = True

    container.register(ServiceDescriptor(ArtifactStore, mock_factory, "singleton"))
    return container


def _clear_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear all LLM-related environment variables."""
    for var in ENV_VARS_TO_CLEAR:
        monkeypatch.delenv(var, raising=False)


# =============================================================================
# can_create() - Configuration Validation
# =============================================================================


class TestLLMServiceFactoryCanCreate:
    """Tests for can_create() configuration validation."""

    def test_can_create_returns_true_for_valid_anthropic_config(self) -> None:
        """Valid Anthropic configuration should allow service creation."""
        container = _create_mock_container()
        config = LLMServiceConfiguration(
            provider="anthropic",
            api_key="test-key",
        )

        factory = LLMServiceFactory(container, config)

        assert factory.can_create() is True

    def test_can_create_returns_true_for_valid_openai_config(self) -> None:
        """Valid OpenAI configuration should allow service creation."""
        container = _create_mock_container()
        config = LLMServiceConfiguration(
            provider="openai",
            api_key="test-key",
        )

        factory = LLMServiceFactory(container, config)

        assert factory.can_create() is True

    def test_can_create_returns_true_for_valid_google_config(self) -> None:
        """Valid Google configuration should allow service creation."""
        container = _create_mock_container()
        config = LLMServiceConfiguration(
            provider="google",
            api_key="test-key",
        )

        factory = LLMServiceFactory(container, config)

        assert factory.can_create() is True

    def test_can_create_returns_false_when_api_key_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Missing API key should return False for graceful degradation."""
        _clear_env_vars(monkeypatch)
        container = _create_mock_container()

        factory = LLMServiceFactory(container)

        assert factory.can_create() is False

    def test_can_create_returns_false_for_invalid_provider(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Invalid provider name should return False."""
        _clear_env_vars(monkeypatch)
        monkeypatch.setenv("LLM_PROVIDER", "invalid_provider")
        container = _create_mock_container()

        factory = LLMServiceFactory(container)

        assert factory.can_create() is False

    def test_can_create_returns_false_when_artifact_store_not_registered(self) -> None:
        """Missing ArtifactStore dependency should return False."""
        container = ServiceContainer()  # Empty container - no ArtifactStore
        config = LLMServiceConfiguration(
            provider="anthropic",
            api_key="test-key",
        )

        factory = LLMServiceFactory(container, config)

        assert factory.can_create() is False


# =============================================================================
# create() - Service Creation
# =============================================================================


class TestLLMServiceFactoryCreate:
    """Tests for create() service creation logic."""

    def test_create_returns_service_for_anthropic_config(self) -> None:
        """Should return LLMService for valid Anthropic config."""
        container = _create_mock_container()
        config = LLMServiceConfiguration(provider="anthropic", api_key="test-key")

        factory = LLMServiceFactory(container, config)
        service = factory.create()

        from waivern_llm.service import LLMService

        assert service is not None
        assert isinstance(service, LLMService)

    def test_create_returns_service_for_openai_config(self) -> None:
        """Should return LLMService for valid OpenAI config."""
        container = _create_mock_container()
        config = LLMServiceConfiguration(provider="openai", api_key="test-key")

        factory = LLMServiceFactory(container, config)
        service = factory.create()

        from waivern_llm.service import LLMService

        assert service is not None
        assert isinstance(service, LLMService)

    def test_create_returns_service_for_google_config(self) -> None:
        """Should return LLMService for valid Google config."""
        container = _create_mock_container()
        config = LLMServiceConfiguration(provider="google", api_key="test-key")

        factory = LLMServiceFactory(container, config)
        service = factory.create()

        from waivern_llm.service import LLMService

        assert service is not None
        assert isinstance(service, LLMService)

    def test_create_returns_none_when_config_invalid(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should return None for invalid config (graceful degradation)."""
        _clear_env_vars(monkeypatch)
        container = _create_mock_container()

        factory = LLMServiceFactory(container)
        service = factory.create()

        assert service is None

    def test_create_returns_none_when_artifact_store_unavailable(self) -> None:
        """Should return None when ArtifactStore cannot be resolved."""
        container = ServiceContainer()  # Empty - no ArtifactStore
        config = LLMServiceConfiguration(provider="anthropic", api_key="test-key")

        factory = LLMServiceFactory(container, config)
        service = factory.create()

        assert service is None
