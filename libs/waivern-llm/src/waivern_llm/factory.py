"""LLM Service factory for dependency injection integration.

This module provides a DI-compatible factory that creates LLMService instances
with the appropriate provider and cache store, resolving dependencies lazily
from the ServiceContainer.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import ValidationError
from waivern_artifact_store.base import ArtifactStore

from waivern_llm.di.configuration import LLMServiceConfiguration
from waivern_llm.providers import (
    AnthropicProvider,
    GoogleProvider,
    LLMProvider,
    OpenAIProvider,
)
from waivern_llm.service import DefaultLLMService, LLMService

if TYPE_CHECKING:
    from waivern_core.services import ServiceContainer

logger = logging.getLogger(__name__)


class LLMServiceFactory:
    """Factory for creating LLMService instances with DI support.

    This factory implements the ServiceFactory[LLMService] protocol,
    resolving dependencies lazily from the ServiceContainer.

    The factory accepts the container at construction and resolves
    ArtifactStore (for caching) in create(), enabling registration
    order independence.

    Example:
        ```python
        from waivern_core.services import ServiceContainer, ServiceDescriptor
        from waivern_artifact_store import ArtifactStore, ArtifactStoreFactory
        from waivern_llm import LLMService, LLMServiceFactory

        container = ServiceContainer()

        # Order doesn't matter
        container.register(
            ServiceDescriptor(LLMService, LLMServiceFactory(container), "singleton")
        )
        container.register(
            ServiceDescriptor(ArtifactStore, ArtifactStoreFactory(), "singleton")
        )

        # Resolution happens lazily
        service = container.get_service(LLMService)
        ```

    """

    def __init__(
        self,
        container: ServiceContainer,
        config: LLMServiceConfiguration | None = None,
    ) -> None:
        """Initialise factory with container and optional configuration.

        Args:
            container: ServiceContainer for resolving dependencies.
            config: Optional explicit configuration. If None, will attempt
                   to create configuration from environment variables.

        """
        self._container = container
        self._config = config

    def _get_config(self) -> LLMServiceConfiguration | None:
        """Get configuration, either from constructor or environment.

        Returns:
            Configuration instance, or None if configuration is invalid.

        """
        if self._config:
            return self._config

        try:
            return LLMServiceConfiguration.from_properties({})
        except ValidationError as e:
            logger.debug(f"Cannot create configuration from environment: {e}")
            return None

    def can_create(self) -> bool:
        """Check if LLM service can be created.

        Validates:
        1. Configuration is valid (provider and API key available)
        2. ArtifactStore dependency can be resolved from container

        Returns:
            True if service can be created, False otherwise.

        """
        if self._get_config() is None:
            return False

        # Check dependency availability
        try:
            self._container.get_service(ArtifactStore)
            return True
        except (KeyError, ValueError):
            logger.debug("Cannot create LLM service - ArtifactStore not available")
            return False

    def create(self) -> LLMService | None:
        """Create an LLMService instance.

        Resolves ArtifactStore from the container for caching, creates
        the appropriate provider based on configuration, and returns
        a DefaultLLMService.

        Returns:
            LLMService instance, or None if service unavailable.

        """
        config = self._get_config()
        if not config:
            logger.debug("Cannot create LLM service - configuration invalid")
            return None

        try:
            # Resolve artifact store from container (lazy resolution)
            store = self._container.get_service(ArtifactStore)

            # Create provider based on configuration
            provider = self.create_provider(config)

            logger.info(
                f"LLM service created (provider={config.provider}, "
                f"model={config.model or 'default'})"
            )

            return DefaultLLMService(
                provider=provider,
                store=store,
                batch_mode=config.batch_mode,
                provider_name=config.provider,
            )

        except Exception as e:
            logger.warning(f"Failed to create LLM service: {e}")
            return None

    @staticmethod
    def create_provider(
        config: LLMServiceConfiguration,
    ) -> LLMProvider:
        """Create the appropriate LLM provider based on configuration.

        Args:
            config: Validated LLM service configuration.

        Returns:
            LLMProvider instance for the configured provider.

        """
        match config.provider:
            case "anthropic":
                return AnthropicProvider(api_key=config.api_key, model=config.model)
            case "openai":
                return OpenAIProvider(
                    api_key=config.api_key, model=config.model, base_url=config.base_url
                )
            case "google":
                return GoogleProvider(api_key=config.api_key, model=config.model)
            case _:
                # LLMServiceConfiguration validates provider, so this is unreachable
                msg = f"Unsupported provider: {config.provider}"
                raise ValueError(msg)
