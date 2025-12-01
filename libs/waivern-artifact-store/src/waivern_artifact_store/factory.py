"""Artifact store factory for dependency injection integration.

This module provides a DI-compatible factory for artifact stores that works
with the waivern-core ServiceContainer.
"""

from __future__ import annotations

import logging

from pydantic import ValidationError

from waivern_artifact_store.base import ArtifactStore
from waivern_artifact_store.configuration import ArtifactStoreConfiguration
from waivern_artifact_store.in_memory import InMemoryArtifactStore

logger = logging.getLogger(__name__)


class ArtifactStoreFactory:
    """Factory for creating artifact store instances with DI support.

    This factory implements the ServiceFactory[ArtifactStore] protocol from
    waivern-core for dependency injection integration.

    Configuration can be provided explicitly or will be read from environment
    variables as a fallback.

    Example:
        ```python
        from waivern_core.services import ServiceContainer, ServiceDescriptor
        from waivern_artifact_store import (
            ArtifactStore,
            ArtifactStoreFactory,
            ArtifactStoreConfiguration
        )

        # Zero-config (reads from environment)
        container = ServiceContainer()
        container.register(
            ServiceDescriptor(ArtifactStore, ArtifactStoreFactory(), "singleton")
        )

        # Explicit configuration
        config = ArtifactStoreConfiguration(backend="memory")
        container.register(
            ServiceDescriptor(ArtifactStore, ArtifactStoreFactory(config), "singleton")
        )

        # Get singleton instance
        store = container.get_service(ArtifactStore)
        ```

    """

    def __init__(self, config: ArtifactStoreConfiguration | None = None) -> None:
        """Initialize factory with optional configuration.

        Args:
            config: Optional explicit configuration. If None, will attempt
                   to create configuration from environment variables.

        """
        self._config = config

    def _get_config(self) -> ArtifactStoreConfiguration | None:
        """Get configuration, either from constructor or environment.

        Returns:
            Configuration instance, or None if configuration is invalid.

        """
        # Use explicit config if provided
        if self._config:
            return self._config

        # Try to create from environment
        try:
            return ArtifactStoreConfiguration.from_properties({})
        except ValidationError as e:
            logger.debug(f"Cannot create configuration from environment: {e}")
            return None

    def can_create(self) -> bool:
        """Check if artifact store can be created with current configuration.

        Validates configuration by attempting to get or create it.
        Configuration validation includes:
        1. Backend is valid (currently only "memory" supported)

        Returns:
            True if service can be created, False otherwise.

        """
        config = self._get_config()
        if not config:
            return False

        # Configuration exists and is valid
        return True

    def create(self) -> ArtifactStore | None:
        """Create an artifact store instance.

        Returns:
            ArtifactStore instance, or None if service unavailable.

        """
        # Get configuration
        config = self._get_config()
        if not config:
            logger.debug("Cannot create artifact store - configuration invalid")
            return None

        if config.backend == "memory":
            logger.info("Creating in-memory artifact store")
            return InMemoryArtifactStore()
        else:
            logger.warning(
                f"Unsupported artifact store backend: '{config.backend}'. "
                f"Supported backends: 'memory'"
            )
            return None
