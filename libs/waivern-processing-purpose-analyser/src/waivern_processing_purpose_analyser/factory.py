"""Factory for creating ProcessingPurposeAnalyser instances with dependency injection."""

from typing import override

from waivern_analysers_shared.utilities import RulesetManager
from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.services.container import ServiceContainer
from waivern_llm import LLMService
from waivern_rulesets import ProcessingPurposeRule

from .analyser import ProcessingPurposeAnalyser
from .types import ProcessingPurposeAnalyserConfig


class ProcessingPurposeAnalyserFactory(ComponentFactory[ProcessingPurposeAnalyser]):
    """Factory for creating ProcessingPurposeAnalyser instances with dependency injection.

    This factory follows proper DI principles:
    - Receives ServiceContainer on construction
    - Resolves dependencies from container when creating components
    - Validates service availability in can_create()

    The factory creates analysers with:
    - LLM service for validation (optional, resolved from container)
    - Pattern matcher instantiated from config (not a service)
    """

    def __init__(self, container: ServiceContainer) -> None:
        """Initialise factory with dependency injection container.

        Args:
            container: Service container for resolving dependencies

        """
        self._container = container

    @override
    def create(self, config: ComponentConfig) -> ProcessingPurposeAnalyser:
        """Create ProcessingPurposeAnalyser instance with injected dependencies.

        Args:
            config: Configuration dict from runbook properties

        Returns:
            Configured ProcessingPurposeAnalyser instance

        Raises:
            ValueError: If configuration is invalid or requirements cannot be met

        """
        if not self.can_create(config):
            raise ValueError("Cannot create analyser with given configuration")

        analyser_config = ProcessingPurposeAnalyserConfig.from_properties(config)

        # Safe to resolve - can_create() already validated availability
        llm_service = (
            self._container.get_service(LLMService)
            if analyser_config.llm_validation.enable_llm_validation
            else None
        )

        return ProcessingPurposeAnalyser(
            config=analyser_config,
            llm_service=llm_service,
        )

    @override
    def can_create(self, config: ComponentConfig) -> bool:
        """Check if factory can create analyser with given configuration.

        Validates:
        1. Configuration structure and required fields
        2. Ruleset exists and can be loaded
        3. LLM service available (if LLM validation enabled)

        Args:
            config: Configuration dict to validate

        Returns:
            True if factory can create analyser, False otherwise

        """
        # Try to parse and validate configuration
        try:
            analyser_config = ProcessingPurposeAnalyserConfig.from_properties(config)
        except Exception:
            return False

        # Validate ruleset exists
        try:
            RulesetManager.get_ruleset(
                analyser_config.pattern_matching.ruleset, ProcessingPurposeRule
            )
        except Exception:
            return False

        # If LLM validation enabled, must have LLM service available in container
        if analyser_config.llm_validation.enable_llm_validation:
            try:
                self._container.get_service(LLMService)
            except (ValueError, KeyError):
                return False

        return True

    @property
    @override
    def component_class(self) -> type[ProcessingPurposeAnalyser]:
        """Get the component class this factory creates."""
        return ProcessingPurposeAnalyser

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        """Declare service dependencies for DI container.

        Returns:
            Dictionary mapping dependency names to their types:
            - "llm_service": LLMService (optional)

        """
        return {
            "llm_service": LLMService,
        }
