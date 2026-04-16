"""Factory for creating PersonalDataAnalyser instances with dependency injection."""

from typing import override

from waivern_analysers_shared.utilities import RulesetManager
from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.services.container import ServiceContainer
from waivern_rulesets import PersonalDataIndicatorRule

from .analyser import PersonalDataAnalyser
from .types import PersonalDataAnalyserConfig


class PersonalDataAnalyserFactory(ComponentFactory[PersonalDataAnalyser]):
    """Factory for creating PersonalDataAnalyser instances.

    The factory takes a ``ServiceContainer`` for symmetry with other
    processor factories (and to support future service dependencies), but
    PersonalDataAnalyser currently has no injected services. LLM dispatch
    is handled by the executor via the DispatcherFactory registry, not
    through this factory.
    """

    def __init__(self, container: ServiceContainer) -> None:
        """Initialise factory.

        Args:
            container: Service container for resolving dependencies (unused today).

        """
        self._container = container

    @override
    def create(self, config: ComponentConfig) -> PersonalDataAnalyser:
        """Create a PersonalDataAnalyser from configuration.

        Args:
            config: Configuration dict from runbook properties.

        Returns:
            Configured PersonalDataAnalyser instance.

        Raises:
            ValueError: If configuration is invalid.

        """
        if not self.can_create(config):
            raise ValueError("Cannot create analyser with given configuration")

        return PersonalDataAnalyser(
            config=PersonalDataAnalyserConfig.from_properties(config),
        )

    @override
    def can_create(self, config: ComponentConfig) -> bool:
        """Check if factory can create analyser with given configuration.

        Validates configuration structure and ruleset availability.
        """
        try:
            analyser_config = PersonalDataAnalyserConfig.from_properties(config)
        except Exception:
            return False

        try:
            RulesetManager.get_ruleset(
                analyser_config.pattern_matching.ruleset, PersonalDataIndicatorRule
            )
        except Exception:
            return False

        return True

    @property
    @override
    def component_class(self) -> type[PersonalDataAnalyser]:
        return PersonalDataAnalyser

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        """Declare service dependencies for the DI container.

        PersonalDataAnalyser has no service dependencies — LLM dispatch is
        driven by the executor via the DispatcherFactory registry.
        """
        return {}
