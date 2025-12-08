"""Factory for creating PersonalDataAnalyser instances with dependency injection."""

from typing import override

from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.services.container import ServiceContainer
from waivern_llm import BaseLLMService

from .analyser import PersonalDataAnalyser
from .types import PersonalDataAnalyserConfig


class PersonalDataAnalyserFactory(ComponentFactory[PersonalDataAnalyser]):
    """Factory for creating PersonalDataAnalyser instances with dependency injection.

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
    def create(self, config: ComponentConfig) -> PersonalDataAnalyser:
        """Create PersonalDataAnalyser instance with injected dependencies.

        Args:
            config: Configuration dict from runbook properties

        Returns:
            Configured PersonalDataAnalyser instance

        Raises:
            ValueError: If configuration is invalid or requirements cannot be met

        """
        # Parse and validate configuration
        analyser_config = PersonalDataAnalyserConfig.from_properties(config)

        # Only resolve LLM service if validation is enabled (lazy loading)
        if analyser_config.llm_validation.enable_llm_validation:
            try:
                llm_service = self._container.get_service(BaseLLMService)
            except (ValueError, KeyError) as e:
                msg = "LLM validation enabled but no LLM service available"
                raise ValueError(msg) from e
        else:
            llm_service = None

        # Create analyser with resolved LLM service
        return PersonalDataAnalyser(
            config=analyser_config,
            llm_service=llm_service,
        )

    @override
    def can_create(self, config: ComponentConfig) -> bool:
        """Check if factory can create analyser with given configuration.

        Args:
            config: Configuration dict to validate

        Returns:
            True if factory can create analyser, False otherwise

        """
        # Try to parse and validate configuration
        try:
            analyser_config = PersonalDataAnalyserConfig.from_properties(config)
        except Exception:
            # Config validation failed
            return False

        # If LLM validation enabled, must have LLM service available in container
        if analyser_config.llm_validation.enable_llm_validation:
            try:
                self._container.get_service(BaseLLMService)
            except (ValueError, KeyError):
                return False

        return True

    @property
    @override
    def component_class(self) -> type[PersonalDataAnalyser]:
        """Get the component class this factory creates."""
        return PersonalDataAnalyser

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        """Declare service dependencies for DI container.

        Returns:
            Dictionary mapping dependency names to their types:
            - "llm_service": BaseLLMService (optional)

        """
        return {
            "llm_service": BaseLLMService,
        }
