"""Factory for creating SQLiteConnector instances with dependency injection."""

from typing import override

from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.services.container import ServiceContainer

from .config import SQLiteConnectorConfig
from .connector import SQLiteConnector


class SQLiteConnectorFactory(ComponentFactory[SQLiteConnector]):
    """Factory for creating SQLiteConnector instances.

    This factory has no service dependencies because SQLite database operations
    require no infrastructure services from the framework.
    """

    def __init__(self, container: ServiceContainer) -> None:
        """Initialise factory with dependency injection container.

        Args:
            container: Service container for resolving dependencies (unused for this factory)

        """
        self._container = container

    @override
    def create(self, config: ComponentConfig) -> SQLiteConnector:
        """Create a SQLiteConnector instance from configuration.

        Args:
            config: Configuration dict from runbook properties

        Returns:
            Configured SQLiteConnector instance

        Raises:
            ValueError: If configuration is invalid

        """
        # Parse and validate configuration
        connector_config = SQLiteConnectorConfig.from_properties(config)

        return SQLiteConnector(connector_config)

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
            SQLiteConnectorConfig.from_properties(config)
        except Exception:
            # Config validation failed
            return False

        return True

    @property
    @override
    def component_class(self) -> type[SQLiteConnector]:
        """Get the component class this factory creates."""
        return SQLiteConnector

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        """Get the service dependencies required by this factory."""
        return {}  # No service dependencies
