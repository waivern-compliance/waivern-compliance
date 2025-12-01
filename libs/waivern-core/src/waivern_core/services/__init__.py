"""Service management and dependency injection infrastructure."""

from waivern_core.services.configuration import (
    BaseComponentConfiguration,
    BaseServiceConfiguration,
)
from waivern_core.services.container import ServiceContainer
from waivern_core.services.lifecycle import ServiceDescriptor
from waivern_core.services.protocols import ServiceFactory, ServiceProvider
from waivern_core.services.registry import ComponentRegistry

__all__ = [
    "BaseComponentConfiguration",
    "BaseServiceConfiguration",
    "ComponentRegistry",
    "ServiceContainer",
    "ServiceDescriptor",
    "ServiceFactory",
    "ServiceProvider",
]
