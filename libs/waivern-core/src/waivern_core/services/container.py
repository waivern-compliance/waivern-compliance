"""Service container for dependency injection."""

from typing import Any

from waivern_core.services.protocols import ServiceFactory


class ServiceContainer:
    """Dependency injection container for managing service lifecycle."""

    def __init__(self) -> None:
        """Initialise the service container."""
        # Internal storage uses Any for heterogeneous type storage
        # Type safety is enforced at the public API level through generics
        self._factories: dict[type, Any] = {}
        self._lifetimes: dict[type, str] = {}
        self._singletons: dict[type, Any] = {}

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
                instance = factory.create()
                if instance is None:
                    msg = f"Factory for {service_type.__name__} returned None - service unavailable"
                    raise ValueError(msg)
                self._singletons[service_type] = instance
            return self._singletons[service_type]
        else:
            # Transient - create new instance
            instance = factory.create()
            if instance is None:
                msg = f"Factory for {service_type.__name__} returned None - service unavailable"
                raise ValueError(msg)
            return instance
