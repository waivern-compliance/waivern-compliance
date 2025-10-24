"""Service management and dependency injection infrastructure."""

from waivern_core.services.container import ServiceContainer
from waivern_core.services.protocols import ServiceFactory

__all__ = ["ServiceContainer", "ServiceFactory"]
