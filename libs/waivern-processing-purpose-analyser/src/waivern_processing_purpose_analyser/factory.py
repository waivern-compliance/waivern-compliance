"""Factory for creating ProcessingPurposeAnalyser instances with dependency injection."""

from typing import override

from waivern_analysers_shared.utilities import RulesetManager
from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.services.container import ServiceContainer
from waivern_rulesets import ProcessingPurposeRule

from .analyser import ProcessingPurposeAnalyser
from .types import ProcessingPurposeAnalyserConfig


class ProcessingPurposeAnalyserFactory(ComponentFactory[ProcessingPurposeAnalyser]):
    """Factory for creating ProcessingPurposeAnalyser instances.

    Takes a ``ServiceContainer`` for symmetry with other processor
    factories; ProcessingPurposeAnalyser currently has no injected services.
    """

    def __init__(self, container: ServiceContainer) -> None:
        """Initialise factory.

        Args:
            container: Service container for resolving dependencies (unused today).

        """
        self._container = container

    @override
    def create(self, config: ComponentConfig) -> ProcessingPurposeAnalyser:
        """Create a ProcessingPurposeAnalyser from configuration."""
        if not self.can_create(config):
            raise ValueError("Cannot create analyser with given configuration")

        return ProcessingPurposeAnalyser(
            config=ProcessingPurposeAnalyserConfig.from_properties(config),
        )

    @override
    def can_create(self, config: ComponentConfig) -> bool:
        """Validate configuration and ruleset availability."""
        try:
            analyser_config = ProcessingPurposeAnalyserConfig.from_properties(config)
        except Exception:
            return False

        try:
            RulesetManager.get_ruleset(
                analyser_config.pattern_matching.ruleset, ProcessingPurposeRule
            )
        except Exception:
            return False

        return True

    @property
    @override
    def component_class(self) -> type[ProcessingPurposeAnalyser]:
        return ProcessingPurposeAnalyser

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        """ProcessingPurposeAnalyser has no service dependencies."""
        return {}
