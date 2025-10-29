"""Factory for creating FilesystemConnector instances with dependency injection."""

from typing import override

from waivern_core import ComponentConfig, ComponentFactory, Schema
from waivern_core.schemas import StandardInputSchema

from .config import FilesystemConnectorConfig
from .connector import FilesystemConnector


class FilesystemConnectorFactory(ComponentFactory[FilesystemConnector]):
    """Factory for creating FilesystemConnector instances.

    This factory has no service dependencies because filesystem operations
    require no infrastructure services.
    """

    @override
    def create(self, config: ComponentConfig) -> FilesystemConnector:
        """Create a FilesystemConnector instance from configuration."""
        if not isinstance(config, FilesystemConnectorConfig):
            msg = f"Expected FilesystemConnectorConfig, got {type(config).__name__}"
            raise TypeError(msg)

        return FilesystemConnector(config)

    @override
    def can_create(self, config: ComponentConfig) -> bool:
        """Check if this factory can create a connector with the given config."""
        return isinstance(config, FilesystemConnectorConfig)

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
        return [StandardInputSchema()]

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        """Get the service dependencies required by this factory."""
        return {}
