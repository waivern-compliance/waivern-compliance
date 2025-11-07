"""Factory for creating PersonalDataAnalyser instances with dependency injection."""

from typing import override

from waivern_core import ComponentConfig, ComponentFactory, Schema
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

        # Resolve LLM service from container
        try:
            llm_service = self._container.get_service(BaseLLMService)
        except (ValueError, KeyError):
            llm_service = None

        # Validate that LLM validation requirements can be met
        if analyser_config.llm_validation.enable_llm_validation and llm_service is None:
            msg = "LLM validation enabled but no LLM service available"
            raise ValueError(msg)

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

    @override
    def get_component_name(self) -> str:
        """Get component type name for registry lookup.

        Returns:
            Component type name: "personal_data_analyser"

        """
        return "personal_data_analyser"

    @override
    def get_input_schemas(self) -> list[Schema]:
        """Get input schemas accepted by created analysers.

        Returns:
            List containing Schema("standard_input", "1.0.0")

        """
        return PersonalDataAnalyser.get_supported_input_schemas()

    @override
    def get_output_schemas(self) -> list[Schema]:
        """Get output schemas produced by created analysers.

        Returns:
            List containing Schema("personal_data_finding", "1.0.0")

        """
        return PersonalDataAnalyser.get_supported_output_schemas()

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
