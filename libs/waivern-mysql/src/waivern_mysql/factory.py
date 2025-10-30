"""Factory for creating MySQLConnector instances with dependency injection."""

from typing import override

from waivern_core import ComponentConfig, ComponentFactory, Schema
from waivern_core.schemas import StandardInputSchema

from .config import MySQLConnectorConfig
from .connector import MySQLConnector


class MySQLConnectorFactory(ComponentFactory[MySQLConnector]):
    """Factory for creating MySQLConnector instances.

    This factory has no service dependencies because MySQL operations
    require no infrastructure services from the framework.
    """

    @override
    def create(self, config: ComponentConfig) -> MySQLConnector:
        """Create a MySQLConnector instance from configuration."""
        if not isinstance(config, MySQLConnectorConfig):
            msg = f"Expected MySQLConnectorConfig, got {type(config).__name__}"
            raise TypeError(msg)

        return MySQLConnector(config)

    @override
    def can_create(self, config: ComponentConfig) -> bool:
        """Check if this factory can create a connector with the given config."""
        return isinstance(config, MySQLConnectorConfig)

    @override
    def get_component_name(self) -> str:
        """Get the component type name for connector registration."""
        return "mysql_connector"

    @override
    def get_input_schemas(self) -> list[Schema]:
        """Get the input schemas this connector accepts."""
        return []  # Connectors extract, don't process

    @override
    def get_output_schemas(self) -> list[Schema]:
        """Get the output schemas this connector produces."""
        return [StandardInputSchema()]

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        """Get the service dependencies required by this factory."""
        return {}  # No service dependencies
