"""Service lifecycle management for dependency injection."""

from dataclasses import dataclass

from waivern_core.services.protocols import ServiceFactory


@dataclass
class ServiceDescriptor[T]:
    """Descriptor for a service registration with lifecycle configuration.

    Attributes:
        service_type: The type of service being registered
        factory: Factory that creates service instances
        lifetime: Service lifetime ("singleton" or "transient")

    """

    service_type: type[T]
    factory: ServiceFactory[T]
    lifetime: str = "singleton"
