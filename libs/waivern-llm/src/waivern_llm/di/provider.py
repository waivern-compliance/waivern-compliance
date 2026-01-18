"""LLM service provider for dependency injection integration.

This module provides a ServiceProvider implementation that wraps the
ServiceContainer to provide exception-safe service retrieval.
"""

from __future__ import annotations

import logging

from waivern_core.services import ServiceContainer

logger = logging.getLogger(__name__)


class LLMServiceProvider:
    """Service provider for LLM services with exception-safe retrieval.

    This provider implements the ServiceProvider protocol from waivern-core,
    wrapping the ServiceContainer to provide graceful degradation. Unlike
    calling container.get_service() directly (which raises exceptions),
    this provider returns None for unavailable services.

    Example:
        ```python
        from waivern_core.services import ServiceContainer
        from waivern_llm.di import LLMServiceProvider
        from waivern_llm.base import BaseLLMService

        container = ServiceContainer()
        # ... register services ...

        provider = LLMServiceProvider(container)
        llm_service = provider.get_service(BaseLLMService)

        if llm_service:
            result = llm_service.invoke(prompt)
        else:
            # Fall back to non-LLM analysis
            result = pattern_match_only(text)
        ```

    """

    def __init__(self, container: ServiceContainer) -> None:
        """Initialise provider with service container.

        Args:
            container: ServiceContainer managing service lifecycle

        """
        self._container: ServiceContainer = container
        logger.debug("LLMServiceProvider initialised")

    def get_service[T](self, service_type: type[T]) -> T | None:
        """Get service instance from container, or None if unavailable.

        This method wraps container.get_service() and handles exceptions
        gracefully, returning None instead of raising. This enables
        graceful degradation when services are unavailable.

        Args:
            service_type: The type of service to retrieve

        Returns:
            Service instance, or None if service unavailable or not registered.

        """
        try:
            service = self._container.get_service(service_type)
            logger.debug("Retrieved service: %s", service_type.__name__)
            return service
        except (ValueError, KeyError) as e:
            logger.debug("Service %s unavailable: %s", service_type.__name__, str(e))
            return None

    def is_available[T](self, service_type: type[T]) -> bool:
        """Check if service type is available.

        This method checks if a service can be retrieved without actually
        retrieving it. It calls get_service() and checks if the result
        is not None.

        Args:
            service_type: The type of service to check

        Returns:
            True if service is available, False otherwise.

        """
        service = self.get_service(service_type)
        return service is not None
