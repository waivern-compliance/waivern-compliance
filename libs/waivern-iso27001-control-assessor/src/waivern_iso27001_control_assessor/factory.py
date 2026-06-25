"""Factory for creating ISO27001Assessor instances."""

from typing import override

from waivern_analysers_shared.utilities import RulesetManager
from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.services.container import ServiceContainer
from waivern_rulesets.iso27001_domains import ISO27001DomainsRule

from .analyser import ISO27001Assessor
from .types import ISO27001AssessorConfig


class ISO27001AssessorFactory(ComponentFactory[ISO27001Assessor]):
    """Factory for creating ISO27001Assessor instances.

    Takes a ``ServiceContainer`` for symmetry with other processor
    factories; ISO27001Assessor currently has no injected services.
    """

    def __init__(self, container: ServiceContainer) -> None:
        """Initialise factory.

        Args:
            container: Service container for resolving dependencies (unused today).

        """
        self._container = container

    @override
    def create(self, config: ComponentConfig) -> ISO27001Assessor:
        """Create an ISO27001Assessor from configuration."""
        return ISO27001Assessor(
            config=ISO27001AssessorConfig.from_properties(config),
        )

    @override
    def can_create(self, config: ComponentConfig) -> bool:
        """Validate configuration and domain ruleset availability."""
        try:
            assessor_config = ISO27001AssessorConfig.from_properties(config)
        except Exception:
            return False

        try:
            RulesetManager.get_ruleset(
                assessor_config.domain_ruleset, ISO27001DomainsRule
            )
        except Exception:
            return False

        return True

    @property
    @override
    def component_class(self) -> type[ISO27001Assessor]:
        return ISO27001Assessor

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        """ISO27001Assessor has no service dependencies."""
        return {}
