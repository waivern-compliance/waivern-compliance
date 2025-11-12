"""Factory for creating SourceCodeAnalyser instances with dependency injection."""

from typing import override

from waivern_core import ComponentConfig, ComponentFactory, Schema
from waivern_core.services.container import ServiceContainer

from .analyser import SourceCodeAnalyser
from .analyser_config import SourceCodeAnalyserConfig


class SourceCodeAnalyserFactory(ComponentFactory[SourceCodeAnalyser]):
    """Factory for creating SourceCodeAnalyser instances.

    This factory follows proper DI principles:
    - Receives ServiceContainer on construction
    - Validates configuration via SourceCodeAnalyserConfig
    - Creates SourceCodeAnalyser with validated config

    The analyser has no external service dependencies.
    """

    def __init__(self, container: ServiceContainer) -> None:
        """Initialise factory with dependency injection container.

        Args:
            container: Service container for resolving dependencies

        """
        self._container = container

    @override
    def create(self, config: ComponentConfig) -> SourceCodeAnalyser:
        """Create SourceCodeAnalyser instance with validated configuration.

        Args:
            config: Configuration dict from runbook properties

        Returns:
            Configured SourceCodeAnalyser instance

        Raises:
            ValueError: If configuration is invalid

        """
        # Parse and validate configuration
        analyser_config = SourceCodeAnalyserConfig.from_properties(config)

        # Create analyser with validated config
        return SourceCodeAnalyser(config=analyser_config)

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
            SourceCodeAnalyserConfig.from_properties(config)
            return True
        except Exception:
            # Config validation failed
            return False

    @override
    def get_component_name(self) -> str:
        """Get component type name for registry lookup.

        Returns:
            Component type name: "source_code_analyser"

        """
        return "source_code_analyser"

    @override
    def get_input_schemas(self) -> list[Schema]:
        """Get input schemas accepted by created analysers.

        Returns:
            List containing Schema("standard_input", "1.0.0")

        """
        return SourceCodeAnalyser.get_supported_input_schemas()

    @override
    def get_output_schemas(self) -> list[Schema]:
        """Get output schemas produced by created analysers.

        Returns:
            List containing Schema("source_code", "1.0.0")

        """
        return SourceCodeAnalyser.get_supported_output_schemas()

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        """Declare service dependencies for DI container.

        Returns:
            Empty dict as SourceCodeAnalyser has no service dependencies

        """
        return {}
