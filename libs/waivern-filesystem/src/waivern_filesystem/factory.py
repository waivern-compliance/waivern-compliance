"""Factory for creating FilesystemConnector instances with dependency injection."""

from typing import override

from waivern_core import ComponentConfig, ComponentFactory, Schema
from waivern_core.services.container import ServiceContainer

from .config import FilesystemConnectorConfig
from .connector import FilesystemConnector


class FilesystemConnectorFactory(ComponentFactory[FilesystemConnector]):
    """Factory for creating FilesystemConnector instances.

    This factory has no service dependencies because filesystem operations
    require no infrastructure services.
    """

    def __init__(self, container: ServiceContainer) -> None:
        """Initialise factory with dependency injection container.

        Args:
            container: Service container for resolving dependencies (unused for this factory)

        """
        self._container = container

    @override
    def create(self, config: ComponentConfig) -> FilesystemConnector:
        """Create a FilesystemConnector instance from configuration.

        Args:
            config: Configuration dict from runbook properties

        Returns:
            Configured FilesystemConnector instance

        Raises:
            ValueError: If configuration is invalid

        """
        # Parse and validate configuration
        connector_config = FilesystemConnectorConfig.from_properties(config)

        return FilesystemConnector(connector_config)

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
            FilesystemConnectorConfig.from_properties(config)
        except Exception:
            # Config validation failed
            return False

        return True

    @override
    def get_component_name(self) -> str:
        """Get the component type name for connector registration."""
        return "filesystem_connector"

    @override
    def get_input_schemas(self) -> list[Schema]:
        """Get the input schemas this connector accepts."""
        return []

    @override
    def get_output_schemas(self) -> list[Schema]:
        """Get the output schemas this connector produces."""
        return [Schema("standard_input", "1.0.0")]

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        """Get the service dependencies required by this factory."""
        return {}
