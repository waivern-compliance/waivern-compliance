"""Factory for creating SourceCodeConnector instances with dependency injection."""

from typing import override

from waivern_core import ComponentConfig, ComponentFactory, Schema

from .config import SourceCodeConnectorConfig
from .connector import SourceCodeConnector
from .schemas import SourceCodeSchema


class SourceCodeConnectorFactory(ComponentFactory[SourceCodeConnector]):
    """Factory for creating SourceCodeConnector instances.

    This factory has no service dependencies because source code parsing
    requires no infrastructure services from the framework.
    """

    @override
    def create(self, config: ComponentConfig) -> SourceCodeConnector:
        """Create a SourceCodeConnector instance from configuration.

        Args:
            config: Configuration dict from runbook properties

        Returns:
            Configured SourceCodeConnector instance

        Raises:
            ValueError: If configuration is invalid

        """
        # Parse and validate configuration
        connector_config = SourceCodeConnectorConfig.from_properties(config)

        return SourceCodeConnector(connector_config)

    @override
    def can_create(self, config: ComponentConfig) -> bool:
        """Check if this factory can create a connector with the given config.

        Args:
            config: Configuration dict to validate

        Returns:
            True if factory can create connector, False otherwise

        """
        # Try to parse and validate configuration
        try:
            SourceCodeConnectorConfig.from_properties(config)
        except Exception:
            # Config validation failed
            return False

        return True

    @override
    def get_component_name(self) -> str:
        """Get the component type name for connector registration."""
        return "source_code_connector"

    @override
    def get_input_schemas(self) -> list[Schema]:
        """Get the input schemas this connector accepts."""
        return []  # Connectors extract, don't process

    @override
    def get_output_schemas(self) -> list[Schema]:
        """Get the output schemas this connector produces."""
        return [SourceCodeSchema()]

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        """Get the service dependencies required by this factory."""
        return {}  # No service dependencies
