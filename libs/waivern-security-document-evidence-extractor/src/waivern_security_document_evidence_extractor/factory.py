"""Factory for creating SecurityDocumentEvidenceExtractor instances."""

from typing import override

from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.services.container import ServiceContainer

from .extractor import SecurityDocumentEvidenceExtractor


class SecurityDocumentEvidenceExtractorFactory(
    ComponentFactory[SecurityDocumentEvidenceExtractor],
):
    """Factory for creating SecurityDocumentEvidenceExtractor instances.

    Full implementation in Step 2.
    """

    def __init__(self, container: ServiceContainer) -> None:
        """Initialise factory with dependency injection container.

        Args:
            container: Service container for resolving dependencies

        """
        self._container = container

    @override
    def create(self, config: ComponentConfig) -> SecurityDocumentEvidenceExtractor:
        """Create extractor instance with injected dependencies.

        Full implementation in Step 2.
        """
        raise NotImplementedError

    @override
    def can_create(self, config: ComponentConfig) -> bool:
        """Check if factory can create extractor with given configuration.

        Full implementation in Step 2.
        """
        return False

    @property
    @override
    def component_class(self) -> type[SecurityDocumentEvidenceExtractor]:
        """Get the component class this factory creates."""
        return SecurityDocumentEvidenceExtractor

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        """Declare service dependencies for DI container."""
        return {}
