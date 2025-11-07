"""Factory for creating DataExportAnalyser instances."""

from typing import override

from waivern_core import ComponentConfig, ComponentFactory, Schema
from waivern_core.services.container import ServiceContainer

from .analyser import DataExportAnalyser
from .types import DataExportAnalyserConfig


class DataExportAnalyserFactory(ComponentFactory[DataExportAnalyser]):
    """Factory for creating DataExportAnalyser instances.

    This factory is a placeholder for the work-in-progress analyser.
    It follows proper DI principles but currently has no dependencies.
    """

    def __init__(self, container: ServiceContainer) -> None:
        """Initialise factory with dependency injection container.

        Args:
            container: Service container for resolving dependencies

        """
        self._container = container

    @override
    def create(self, config: ComponentConfig) -> DataExportAnalyser:
        """Create DataExportAnalyser instance.

        Args:
            config: Configuration dict from runbook properties

        Returns:
            Configured DataExportAnalyser instance (not yet functional)

        Raises:
            ValueError: If configuration is invalid

        """
        # Parse and validate configuration
        analyser_config = DataExportAnalyserConfig.from_properties(config)

        # Create analyser
        return DataExportAnalyser(config=analyser_config)

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
            DataExportAnalyserConfig.from_properties(config)
        except Exception:
            # Config validation failed
            return False

        return True

    @override
    def get_component_name(self) -> str:
        """Get component type name for registry lookup.

        Returns:
            Component type name: "data_export_analyser"

        """
        return "data_export_analyser"

    @override
    def get_input_schemas(self) -> list[Schema]:
        """Get input schemas accepted by created analysers.

        Returns:
            Empty list - analyser not yet implemented

        """
        return DataExportAnalyser.get_supported_input_schemas()

    @override
    def get_output_schemas(self) -> list[Schema]:
        """Get output schemas produced by created analysers.

        Returns:
            Empty list - analyser not yet implemented

        """
        return DataExportAnalyser.get_supported_output_schemas()

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        """Declare service dependencies for DI container.

        Returns:
            Empty dict - no service dependencies yet

        """
        return {}
