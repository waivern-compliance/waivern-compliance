"""Service container for dependency injection."""

import logging
from typing import Any

from waivern_core.services.protocols import ServiceFactory

logger = logging.getLogger(__name__)


class ServiceContainer:
    """Dependency injection container for managing service lifecycle."""

    def __init__(self) -> None:
        """Initialise the service container."""
        # Internal storage uses Any for heterogeneous type storage
        # Type safety is enforced at the public API level through generics
        self._factories: dict[type, Any] = {}
        self._lifetimes: dict[type, str] = {}
        self._singletons: dict[type, Any] = {}
        logger.debug("ServiceContainer initialized")

    def register[T](
        self,
        service_type: type[T],
        factory: ServiceFactory[T],
        lifetime: str = "singleton",
    ) -> None:
        """Register a service factory with the container.

        Args:
            service_type: The type of service being registered
            factory: Factory that creates service instances
            lifetime: Service lifetime ("singleton" or "transient")

        """
        self._factories[service_type] = factory
        self._lifetimes[service_type] = lifetime
        logger.debug(
            "Registered service: %s with lifetime: %s",
            service_type.__name__,
            lifetime,
        )

    def get_service[T](self, service_type: type[T]) -> T:
        """Get a service instance from the container.

        Args:
            service_type: The type of service to retrieve

        Returns:
            Service instance

        Raises:
            ValueError: If factory returns None (service unavailable)

        """
        factory = self._factories[service_type]
        lifetime = self._lifetimes[service_type]

        if lifetime == "singleton":
            # Check if singleton already created
            if service_type not in self._singletons:
                # Create and cache singleton
                logger.debug("Creating singleton service: %s", service_type.__name__)
                instance = factory.create()
                if instance is None:
                    logger.error(
                        "Factory for %s returned None - service unavailable",
                        service_type.__name__,
                    )
                    msg = f"Factory for {service_type.__name__} returned None - service unavailable"
                    raise ValueError(msg)
                self._singletons[service_type] = instance
                logger.debug(
                    "Singleton service created and cached: %s", service_type.__name__
                )
            else:
                logger.debug(
                    "Returning cached singleton service: %s", service_type.__name__
                )
            return self._singletons[service_type]
        else:
            # Transient - create new instance
            logger.debug("Creating transient service: %s", service_type.__name__)
            instance = factory.create()
            if instance is None:
                logger.error(
                    "Factory for %s returned None - service unavailable",
                    service_type.__name__,
                )
                msg = f"Factory for {service_type.__name__} returned None - service unavailable"
                raise ValueError(msg)
            return instance
