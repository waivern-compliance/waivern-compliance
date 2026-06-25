"""Factory for creating SecurityDocumentEvidenceExtractor instances."""

import logging
from typing import override

from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.services.container import ServiceContainer

from .extractor import SecurityDocumentEvidenceExtractor
from .types import SecurityDocumentEvidenceExtractorConfig

logger = logging.getLogger(__name__)


class SecurityDocumentEvidenceExtractorFactory(
    ComponentFactory[SecurityDocumentEvidenceExtractor],
):
    """Factory for creating SecurityDocumentEvidenceExtractor instances.

    Takes a ``ServiceContainer`` for symmetry with other processor
    factories; SecurityDocumentEvidenceExtractor currently has no injected
    services.
    """

    def __init__(self, container: ServiceContainer) -> None:
        """Initialise factory.

        Args:
            container: Service container for resolving dependencies (unused today).

        """
        self._container = container

    @override
    def create(self, config: ComponentConfig) -> SecurityDocumentEvidenceExtractor:
        """Create a SecurityDocumentEvidenceExtractor from configuration."""
        return SecurityDocumentEvidenceExtractor(
            config=SecurityDocumentEvidenceExtractorConfig.from_properties(config),
        )

    @override
    def can_create(self, config: ComponentConfig) -> bool:
        """Validate configuration parsing."""
        try:
            SecurityDocumentEvidenceExtractorConfig.from_properties(config)
        except Exception:
            return False

        return True

    @property
    @override
    def component_class(self) -> type[SecurityDocumentEvidenceExtractor]:
        return SecurityDocumentEvidenceExtractor

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        """SecurityDocumentEvidenceExtractor has no service dependencies."""
        return {}
