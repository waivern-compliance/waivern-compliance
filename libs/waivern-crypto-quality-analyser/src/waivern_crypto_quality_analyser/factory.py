"""Factory for creating CryptoQualityAnalyser instances."""

from typing import override

from waivern_analysers_shared.utilities import RulesetManager
from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.services.container import ServiceContainer
from waivern_rulesets.crypto_quality_indicator import CryptoQualityIndicatorRule

from .analyser import CryptoQualityAnalyser
from .types import CryptoQualityAnalyserConfig


class CryptoQualityAnalyserFactory(ComponentFactory[CryptoQualityAnalyser]):
    """Factory for creating CryptoQualityAnalyser instances.

    No LLM service dependency — CryptoQualityAnalyser is fully deterministic.
    The factory only validates config structure and ruleset availability.
    """

    def __init__(self, container: ServiceContainer) -> None:
        """Initialise factory with dependency injection container.

        Args:
            container: Service container (unused; retained for DI protocol consistency)

        """
        self._container = container

    @override
    def create(self, config: ComponentConfig) -> CryptoQualityAnalyser:
        """Create CryptoQualityAnalyser instance.

        Args:
            config: Configuration dict from runbook properties

        Returns:
            Configured CryptoQualityAnalyser instance

        Raises:
            ValueError: If configuration is invalid or ruleset cannot be loaded

        """
        if not self.can_create(config):
            raise ValueError("Cannot create analyser with given configuration")

        analyser_config = CryptoQualityAnalyserConfig.from_properties(config)
        return CryptoQualityAnalyser(config=analyser_config)

    @override
    def can_create(self, config: ComponentConfig) -> bool:
        """Check if factory can create analyser with given configuration.

        Validates:
        1. Configuration structure and required fields
        2. Ruleset exists and can be loaded

        Args:
            config: Configuration dict to validate

        Returns:
            True if factory can create analyser, False otherwise

        """
        try:
            analyser_config = CryptoQualityAnalyserConfig.from_properties(config)
        except Exception:
            return False

        try:
            RulesetManager.get_ruleset(
                analyser_config.pattern_matching.ruleset, CryptoQualityIndicatorRule
            )
        except Exception:
            return False

        return True

    @property
    @override
    def component_class(self) -> type[CryptoQualityAnalyser]:
        """Get the component class this factory creates."""
        return CryptoQualityAnalyser

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        """Declare service dependencies for DI container.

        CryptoQualityAnalyser has no service dependencies — it is
        fully self-contained with pattern matching and a YAML ruleset.

        Returns:
            Empty dict (no service dependencies)

        """
        return {}
