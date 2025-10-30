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
        """Create a SourceCodeConnector instance from configuration."""
        if not isinstance(config, SourceCodeConnectorConfig):
            msg = f"Expected SourceCodeConnectorConfig, got {type(config).__name__}"
            raise TypeError(msg)

        return SourceCodeConnector(config)

    @override
    def can_create(self, config: ComponentConfig) -> bool:
        """Check if this factory can create a connector with the given config."""
        return isinstance(config, SourceCodeConnectorConfig)

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
