"""Tests for LLMDispatcherFactory.

Business behaviour: Creates LLMDispatcher instances with the correct provider
and cache store, resolving dependencies lazily from the ServiceContainer.
Follows the same ServiceFactory pattern as LLMServiceFactory.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

from waivern_artifact_store.base import ArtifactStore
from waivern_core.services import ServiceContainer, ServiceDescriptor

from waivern_llm.di.configuration import LLMServiceConfiguration
from waivern_llm.dispatcher_factory import LLMDispatcherFactory

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


class TestLLMDispatcherFactoryCanCreate:
    """Tests for can_create() configuration validation."""

    def test_can_create_returns_true_for_valid_config(self) -> None:
        """Valid config with ArtifactStore registered should allow creation."""
        container = _create_mock_container()
        config = LLMServiceConfiguration(provider="anthropic", api_key="test-key")

        factory = LLMDispatcherFactory(container, config)

        assert factory.can_create() is True

    def test_can_create_returns_false_when_config_invalid(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Missing config and no env vars should return False."""
        _clear_env_vars(monkeypatch)
        container = _create_mock_container()

        factory = LLMDispatcherFactory(container)

        assert factory.can_create() is False

    def test_can_create_returns_false_when_store_not_registered(self) -> None:
        """Valid config but no ArtifactStore should return False."""
        container = ServiceContainer()
        config = LLMServiceConfiguration(provider="anthropic", api_key="test-key")

        factory = LLMDispatcherFactory(container, config)

        assert factory.can_create() is False


# =============================================================================
# create() - Dispatcher Creation
# =============================================================================


class TestLLMDispatcherFactoryCreate:
    """Tests for create() dispatcher creation logic."""

    def test_create_returns_dispatcher_for_valid_config(self) -> None:
        """Should return LLMDispatcher for valid config with all dependencies."""
        container = _create_mock_container()
        config = LLMServiceConfiguration(provider="anthropic", api_key="test-key")

        factory = LLMDispatcherFactory(container, config)
        dispatcher = factory.create()

        from waivern_llm.dispatcher import LLMDispatcher

        assert dispatcher is not None
        assert isinstance(dispatcher, LLMDispatcher)

    def test_create_returns_none_when_config_invalid(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should return None for invalid config (graceful degradation)."""
        _clear_env_vars(monkeypatch)
        container = _create_mock_container()

        factory = LLMDispatcherFactory(container)
        dispatcher = factory.create()

        assert dispatcher is None

    def test_create_returns_none_when_store_unavailable(self) -> None:
        """Should return None when ArtifactStore cannot be resolved."""
        container = ServiceContainer()
        config = LLMServiceConfiguration(provider="anthropic", api_key="test-key")

        factory = LLMDispatcherFactory(container, config)
        dispatcher = factory.create()

        assert dispatcher is None
