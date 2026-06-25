"""Factory for creating DataSubjectAnalyser instances with dependency injection."""

from typing import override

from waivern_analysers_shared.utilities import RulesetManager
from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.services.container import ServiceContainer
from waivern_rulesets.data_subject_indicator import DataSubjectIndicatorRule

from .analyser import DataSubjectAnalyser
from .types import DataSubjectAnalyserConfig


class DataSubjectAnalyserFactory(ComponentFactory[DataSubjectAnalyser]):
    """Factory for creating DataSubjectAnalyser instances.

    Takes a ``ServiceContainer`` for symmetry with other processor
    factories; DataSubjectAnalyser currently has no injected services.
    """

    def __init__(self, container: ServiceContainer) -> None:
        """Initialise factory.

        Args:
            container: Service container for resolving dependencies (unused today).

        """
        self._container = container

    @override
    def create(self, config: ComponentConfig) -> DataSubjectAnalyser:
        """Create a DataSubjectAnalyser from configuration."""
        return DataSubjectAnalyser(
            config=DataSubjectAnalyserConfig.from_properties(config),
        )

    @override
    def can_create(self, config: ComponentConfig) -> bool:
        """Validate configuration and ruleset availability."""
        try:
            analyser_config = DataSubjectAnalyserConfig.from_properties(config)
        except Exception:
            return False

        try:
            RulesetManager.get_ruleset(
                analyser_config.pattern_matching.ruleset, DataSubjectIndicatorRule
            )
        except Exception:
            return False

        return True

    @property
    @override
    def component_class(self) -> type[DataSubjectAnalyser]:
        return DataSubjectAnalyser

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        """DataSubjectAnalyser has no service dependencies."""
        return {}
