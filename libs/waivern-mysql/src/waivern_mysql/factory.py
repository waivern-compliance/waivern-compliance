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
        """Create a MySQLConnector instance from configuration.

        Args:
            config: Configuration dict from runbook properties

        Returns:
            Configured MySQLConnector instance

        Raises:
            ValueError: If configuration is invalid

        """
        # Parse and validate configuration
        connector_config = MySQLConnectorConfig.from_properties(config)

        return MySQLConnector(connector_config)

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
            MySQLConnectorConfig.from_properties(config)
        except Exception:
            # Config validation failed
            return False

        return True

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
