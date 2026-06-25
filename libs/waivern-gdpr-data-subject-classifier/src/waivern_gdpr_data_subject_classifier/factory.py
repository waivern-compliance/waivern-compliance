"""Factory for creating GDPRDataSubjectClassifier instances."""

from typing import override

from waivern_analysers_shared.utilities import RulesetManager
from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.services.container import ServiceContainer
from waivern_rulesets import GDPRDataSubjectClassificationRule

from .classifier import GDPRDataSubjectClassifier
from .types import GDPRDataSubjectClassifierConfig


class GDPRDataSubjectClassifierFactory(ComponentFactory[GDPRDataSubjectClassifier]):
    """Factory for creating GDPRDataSubjectClassifier instances.

    Takes a ``ServiceContainer`` for symmetry with other processor
    factories; GDPRDataSubjectClassifier currently has no injected services.
    """

    def __init__(self, container: ServiceContainer) -> None:
        """Initialise factory.

        Args:
            container: Service container for resolving dependencies (unused today).

        """
        self._container = container

    @override
    def create(self, config: ComponentConfig) -> GDPRDataSubjectClassifier:
        """Create a GDPRDataSubjectClassifier from configuration."""
        return GDPRDataSubjectClassifier(
            config=GDPRDataSubjectClassifierConfig.from_properties(config),
        )

    @override
    def can_create(self, config: ComponentConfig) -> bool:
        """Validate configuration and ruleset availability."""
        try:
            classifier_config = GDPRDataSubjectClassifierConfig.from_properties(config)
        except Exception:
            return False

        try:
            RulesetManager.get_ruleset(
                classifier_config.ruleset, GDPRDataSubjectClassificationRule
            )
        except Exception:
            return False

        return True

    @property
    @override
    def component_class(self) -> type[GDPRDataSubjectClassifier]:
        return GDPRDataSubjectClassifier

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        """GDPRDataSubjectClassifier has no service dependencies."""
        return {}
