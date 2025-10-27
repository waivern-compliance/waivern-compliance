"""LLM service factory for dependency injection integration.

This module provides a DI-compatible factory that wraps the existing waivern-llm
service factory to work with the waivern-core ServiceContainer.
"""

from __future__ import annotations

import logging

from pydantic import ValidationError

from waivern_llm.base import BaseLLMService
from waivern_llm.di.configuration import LLMServiceConfiguration
from waivern_llm.factory import LLMServiceFactory as UnderlyingFactory

logger = logging.getLogger(__name__)


class LLMServiceFactory:
    """Factory for creating LLM service instances with DI support.

    This factory implements the ServiceFactory[BaseLLMService] protocol from
    waivern-core, wrapping the existing waivern_llm.factory.LLMServiceFactory
    to provide graceful degradation and health checking.

    Unlike the underlying factory which raises exceptions on configuration errors,
    this DI factory returns None to enable graceful degradation.

    Configuration can be provided explicitly or will be read from environment
    variables as a fallback.

    Example:
        ```python
        from waivern_core.services import ServiceContainer
        from waivern_llm.di import LLMServiceFactory, LLMServiceConfiguration
        from waivern_llm.base import BaseLLMService

        # Zero-config (reads from environment)
        container = ServiceContainer()
        container.register(
            BaseLLMService,
            LLMServiceFactory(),
            lifetime="singleton"
        )

        # Explicit configuration
        config = LLMServiceConfiguration(
            provider="anthropic",
            api_key="sk-..."
        )
        container.register(
            BaseLLMService,
            LLMServiceFactory(config),
            lifetime="singleton"
        )

        llm_service = container.get_service(BaseLLMService)
        if llm_service:
            result = llm_service.analyse_data("text", "prompt")
        ```

    """

    def __init__(self, config: LLMServiceConfiguration | None = None) -> None:
        """Initialize factory with optional configuration.

        Args:
            config: Optional explicit configuration. If None, will attempt
                   to create configuration from environment variables.

        """
        self._config = config

    def _get_config(self) -> LLMServiceConfiguration | None:
        """Get configuration, either from constructor or environment.

        Returns:
            Configuration instance, or None if configuration is invalid.

        """
        # Use explicit config if provided
        if self._config:
            return self._config

        # Try to create from environment
        try:
            return LLMServiceConfiguration.from_properties({})
        except ValidationError as e:
            logger.debug(f"Cannot create configuration from environment: {e}")
            return None

    def can_create(self) -> bool:
        """Check if LLM service can be created with current configuration.

        Validates configuration by attempting to get or create it.
        Configuration validation includes:
        1. Provider is valid (anthropic, openai, or google)
        2. Required API key for the provider is available

        Returns:
            True if service can be created, False otherwise.

        """
        config = self._get_config()
        if not config:
            return False

        # Configuration exists and is valid
        return True

    def create(self) -> BaseLLMService | None:
        """Create an LLM service instance.

        Returns:
            BaseLLMService instance, or None if service unavailable.

        """
        # Get configuration
        config = self._get_config()
        if not config:
            logger.debug("Cannot create LLM service - configuration invalid")
            return None

        try:
            # Use the existing factory to create the service
            # Pass environment variables (underlying factory reads from env)
            service = UnderlyingFactory.create_service()
            logger.info(
                f"LLM service created successfully via DI factory "
                f"(provider={config.provider}, model={config.get_default_model()})"
            )
            return service

        except Exception as e:
            logger.warning(f"Failed to create LLM service: {e}")
            return None
