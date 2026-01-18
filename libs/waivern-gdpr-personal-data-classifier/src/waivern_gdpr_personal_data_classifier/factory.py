"""Factory for creating GDPRPersonalDataClassifier instances."""

from typing import override

from waivern_analysers_shared.utilities import RulesetManager
from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.services.container import ServiceContainer
from waivern_rulesets import GDPRPersonalDataClassificationRule

from .classifier import GDPRPersonalDataClassifier
from .types import GDPRPersonalDataClassifierConfig


class GDPRPersonalDataClassifierFactory(ComponentFactory[GDPRPersonalDataClassifier]):
    """Factory for creating GDPRPersonalDataClassifier instances.

    This factory parses configuration from runbook properties and creates
    classifiers with the specified ruleset URI.
    """

    def __init__(self, container: ServiceContainer) -> None:
        """Initialise factory with dependency injection container.

        Args:
            container: Service container (not used but required by interface)

        """
        self._container = container

    @override
    def create(self, config: ComponentConfig) -> GDPRPersonalDataClassifier:
        """Create GDPRPersonalDataClassifier instance.

        Args:
            config: Configuration dict from runbook properties

        Returns:
            Configured GDPRPersonalDataClassifier instance

        """
        classifier_config = GDPRPersonalDataClassifierConfig.from_properties(config)
        return GDPRPersonalDataClassifier(config=classifier_config)

    @override
    def can_create(self, config: ComponentConfig) -> bool:
        """Check if factory can create classifier with given configuration.

        Validates:
        1. Configuration structure and required fields
        2. Ruleset exists and can be loaded

        Args:
            config: Configuration dict to validate

        Returns:
            True if configuration is valid and ruleset exists, False otherwise

        """
        try:
            classifier_config = GDPRPersonalDataClassifierConfig.from_properties(config)
        except Exception:
            return False

        # Validate ruleset exists
        try:
            RulesetManager.get_ruleset(
                classifier_config.ruleset, GDPRPersonalDataClassificationRule
            )
        except Exception:
            return False

        return True

    @property
    @override
    def component_class(self) -> type[GDPRPersonalDataClassifier]:
        """Get the component class this factory creates."""
        return GDPRPersonalDataClassifier

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        """Declare service dependencies for DI container.

        Returns:
            Empty dictionary as this classifier has no external dependencies

        """
        return {}
