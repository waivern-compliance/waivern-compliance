"""LLM Dispatcher factory for dependency injection integration.

This module provides a DI-compatible factory that creates LLMDispatcher
instances with the appropriate provider and cache store, resolving
dependencies lazily from the ServiceContainer.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import ValidationError
from waivern_artifact_store.base import ArtifactStore

from waivern_llm.di.configuration import LLMServiceConfiguration
from waivern_llm.dispatcher import LLMDispatcher
from waivern_llm.providers import create_provider

if TYPE_CHECKING:
    from waivern_core.services import ServiceContainer

logger = logging.getLogger(__name__)


class LLMDispatcherFactory:
    """Factory for creating LLMDispatcher instances with DI support.

    Implements the ``ServiceFactory[LLMDispatcher]`` protocol, resolving
    dependencies lazily from the ``ServiceContainer``. Follows the same
    pattern as ``LLMServiceFactory``.

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
        """Check if LLM dispatcher can be created.

        Validates:
        1. Configuration is valid (provider and API key available)
        2. ArtifactStore dependency can be resolved from container

        Returns:
            True if dispatcher can be created, False otherwise.

        """
        if self._get_config() is None:
            return False

        try:
            self._container.get_service(ArtifactStore)
            return True
        except (KeyError, ValueError):
            logger.debug("Cannot create LLM dispatcher - ArtifactStore not available")
            return False

    def create(self) -> LLMDispatcher | None:
        """Create an LLMDispatcher instance.

        Resolves ArtifactStore from the container for caching, creates
        the appropriate provider based on configuration, and returns
        an LLMDispatcher.

        Returns:
            LLMDispatcher instance, or None if unavailable.

        """
        config = self._get_config()
        if not config:
            logger.debug("Cannot create LLM dispatcher - configuration invalid")
            return None

        try:
            store = self._container.get_service(ArtifactStore)
            provider = create_provider(config)

            logger.info(
                f"LLM dispatcher created (provider={config.provider}, "
                f"model={config.model or 'default'})"
            )

            return LLMDispatcher(
                provider=provider,
                store=store,
                batch_mode=config.batch_mode,
            )

        except Exception as e:
            logger.warning(f"Failed to create LLM dispatcher: {e}")
            return None
