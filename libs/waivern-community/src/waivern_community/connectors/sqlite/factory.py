"""Factory for creating SQLiteConnector instances with dependency injection."""

from typing import override

from waivern_core import ComponentConfig, ComponentFactory, Schema
from waivern_core.schemas import StandardInputSchema

from .config import SQLiteConnectorConfig
from .connector import SQLiteConnector


class SQLiteConnectorFactory(ComponentFactory[SQLiteConnector]):
    """Factory for creating SQLiteConnector instances.

    This factory has no service dependencies because SQLite database operations
    require no infrastructure services from the framework.
    """

    @override
    def create(self, config: ComponentConfig) -> SQLiteConnector:
        """Create a SQLiteConnector instance from configuration."""
        if not isinstance(config, SQLiteConnectorConfig):
            msg = f"Expected SQLiteConnectorConfig, got {type(config).__name__}"
            raise TypeError(msg)

        return SQLiteConnector(config)

    @override
    def can_create(self, config: ComponentConfig) -> bool:
        """Check if this factory can create a connector with the given config."""
        return isinstance(config, SQLiteConnectorConfig)

    @override
    def get_component_name(self) -> str:
        """Get the component type name for connector registration."""
        return "sqlite_connector"

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
