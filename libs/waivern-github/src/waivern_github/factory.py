"""Factory for creating GitHubConnector instances with dependency injection."""

from typing import override

from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.services.container import ServiceContainer

from waivern_github.config import GitHubConnectorConfig
from waivern_github.connector import GitHubConnector


class GitHubConnectorFactory(ComponentFactory[GitHubConnector]):
    """Factory for creating GitHubConnector instances.

    This factory has no service dependencies because GitHub operations
    require no infrastructure services from the framework.
    """

    def __init__(self, container: ServiceContainer) -> None:
        """Initialise factory with dependency injection container.

        Args:
            container: Service container for resolving dependencies (unused)

        """
        self._container = container

    @override
    def create(self, config: ComponentConfig) -> GitHubConnector:
        """Create a GitHubConnector instance from configuration.

        Args:
            config: Configuration dict from runbook properties

        Returns:
            Configured GitHubConnector instance

        Raises:
            ConnectorConfigError: If configuration is invalid

        """
        connector_config = GitHubConnectorConfig.from_properties(config)
        return GitHubConnector(connector_config)

    @override
    def can_create(self, config: ComponentConfig) -> bool:
        """Check if this factory can create a connector with the given config.

        Args:
            config: Configuration dict to validate

        Returns:
            True if factory can create connector, False otherwise

        """
        try:
            GitHubConnectorConfig.from_properties(config)
        except Exception:
            return False
        return True

    @property
    @override
    def component_class(self) -> type[GitHubConnector]:
        """Get the component class this factory creates."""
        return GitHubConnector

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        """Get the service dependencies required by this factory."""
        return {}  # No service dependencies
