"""Factory for creating SecurityDocumentEvidenceExtractor instances."""

import logging
from typing import override

from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.services.container import ServiceContainer
from waivern_llm import LLMService

from .extractor import SecurityDocumentEvidenceExtractor
from .types import SecurityDocumentEvidenceExtractorConfig

logger = logging.getLogger(__name__)


class SecurityDocumentEvidenceExtractorFactory(
    ComponentFactory[SecurityDocumentEvidenceExtractor],
):
    """Factory for creating SecurityDocumentEvidenceExtractor instances.

    Resolves LLMService from the DI container when LLM classification
    is enabled. When disabled, the extractor runs without LLM and assigns
    empty security_domains to all documents.
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

        Args:
            config: Configuration dict from runbook properties.

        Returns:
            Configured SecurityDocumentEvidenceExtractor instance.

        Raises:
            ValueError: If configuration is invalid or requirements cannot be met.

        """
        if not self.can_create(config):
            raise ValueError("Cannot create extractor with given configuration")

        extractor_config = SecurityDocumentEvidenceExtractorConfig.from_properties(
            config
        )

        llm_service = (
            self._container.get_service(LLMService)
            if extractor_config.enable_llm_classification
            else None
        )

        return SecurityDocumentEvidenceExtractor(
            config=extractor_config,
            llm_service=llm_service,
        )

    @override
    def can_create(self, config: ComponentConfig) -> bool:
        """Check if factory can create extractor with given configuration.

        Validates:
        1. Configuration structure
        2. LLM service available (if classification enabled)

        Args:
            config: Configuration dict to validate.

        Returns:
            True if factory can create extractor, False otherwise.

        """
        try:
            extractor_config = SecurityDocumentEvidenceExtractorConfig.from_properties(
                config
            )
        except Exception:
            return False

        if extractor_config.enable_llm_classification:
            try:
                self._container.get_service(LLMService)
            except (ValueError, KeyError):
                return False

        return True

    @property
    @override
    def component_class(self) -> type[SecurityDocumentEvidenceExtractor]:
        """Get the component class this factory creates."""
        return SecurityDocumentEvidenceExtractor

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        """Declare service dependencies for DI container."""
        return {
            "llm_service": LLMService,
        }
