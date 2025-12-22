"""Tests for ComponentRegistry - centralised component discovery.

These tests verify the registry's ability to:
- Expose the underlying ServiceContainer
- Lazily discover components from entry points
- Cache discovered factories after first access
"""

from unittest.mock import MagicMock, patch

from waivern_core.services import ComponentRegistry, ServiceContainer

# =============================================================================
# Component Registry Core
# =============================================================================


class TestComponentRegistry:
    """Test suite for ComponentRegistry."""

    def test_container_property_returns_underlying_container(self) -> None:
        """Verify registry exposes the underlying ServiceContainer."""
        # Arrange
        container = ServiceContainer()

        # Act
        registry = ComponentRegistry(container)

        # Assert
        assert registry.container is container

    def test_factories_not_discovered_on_construction(self) -> None:
        """Verify factories are lazily discovered, not during __init__."""
        # Arrange
        container = ServiceContainer()

        with patch("waivern_core.services.registry.entry_points") as mock_ep:
            mock_ep.return_value = []

            # Act - construct registry
            _ = ComponentRegistry(container)

            # Assert - entry_points should NOT have been called during construction
            mock_ep.assert_not_called()

    def test_connector_factories_triggers_discovery(self) -> None:
        """Verify accessing connector_factories triggers entry point discovery."""
        # Arrange
        container = ServiceContainer()

        with patch("waivern_core.services.registry.entry_points") as mock_ep:
            mock_ep.return_value = []
            registry = ComponentRegistry(container)

            # Act - access connector_factories
            _ = registry.connector_factories

            # Assert - entry_points called for schemas, connectors, processors
            assert mock_ep.call_count == 3

    def test_processor_factories_triggers_discovery(self) -> None:
        """Verify accessing processor_factories triggers entry point discovery."""
        # Arrange
        container = ServiceContainer()

        with patch("waivern_core.services.registry.entry_points") as mock_ep:
            mock_ep.return_value = []
            registry = ComponentRegistry(container)

            # Act - access processor_factories
            _ = registry.processor_factories

            # Assert - entry_points called for schemas, connectors, processors
            assert mock_ep.call_count == 3

    def test_discovery_called_only_once(self) -> None:
        """Verify _discover_components called exactly once despite multiple accesses."""
        # Arrange
        container = ServiceContainer()
        registry = ComponentRegistry(container)

        with patch("waivern_core.services.registry.entry_points") as mock_ep:
            mock_ep.return_value = []

            # Act - access factories multiple times
            _ = registry.connector_factories
            _ = registry.processor_factories
            _ = registry.connector_factories
            _ = registry.processor_factories

        # Assert - entry_points called only 3 times (schemas, connectors, processors)
        assert mock_ep.call_count == 3

    def test_discovered_connector_factory_accessible_by_name(self) -> None:
        """Verify discovered connector factories are accessible by entry point name."""
        # Arrange
        container = ServiceContainer()
        registry = ComponentRegistry(container)

        mock_factory_class = MagicMock()
        mock_factory_instance = MagicMock()
        mock_factory_class.return_value = mock_factory_instance

        mock_ep = MagicMock()
        mock_ep.name = "test_connector"
        mock_ep.load.return_value = mock_factory_class

        with patch("waivern_core.services.registry.entry_points") as mock_entry_points:
            mock_entry_points.side_effect = lambda group: (
                [mock_ep] if group == "waivern.connectors" else []
            )

            # Act
            factories = registry.connector_factories

        # Assert
        assert "test_connector" in factories
        assert factories["test_connector"] is mock_factory_instance

    def test_discovered_processor_factory_accessible_by_name(self) -> None:
        """Verify discovered processor factories are accessible by entry point name."""
        # Arrange
        container = ServiceContainer()
        registry = ComponentRegistry(container)

        mock_factory_class = MagicMock()
        mock_factory_instance = MagicMock()
        mock_factory_class.return_value = mock_factory_instance

        mock_ep = MagicMock()
        mock_ep.name = "test_processor"
        mock_ep.load.return_value = mock_factory_class

        with patch("waivern_core.services.registry.entry_points") as mock_entry_points:
            mock_entry_points.side_effect = lambda group: (
                [mock_ep] if group == "waivern.processors" else []
            )

            # Act
            factories = registry.processor_factories

        # Assert
        assert "test_processor" in factories
        assert factories["test_processor"] is mock_factory_instance

    def test_factory_instantiated_with_container(self) -> None:
        """Verify factory classes are instantiated with the ServiceContainer."""
        # Arrange
        container = ServiceContainer()
        registry = ComponentRegistry(container)

        mock_factory_class = MagicMock()

        mock_ep = MagicMock()
        mock_ep.name = "test_connector"
        mock_ep.load.return_value = mock_factory_class

        with patch("waivern_core.services.registry.entry_points") as mock_entry_points:
            mock_entry_points.side_effect = lambda group: (
                [mock_ep] if group == "waivern.connectors" else []
            )

            # Act
            _ = registry.connector_factories

        # Assert - factory class instantiated with container
        mock_factory_class.assert_called_once_with(container)


# =============================================================================
# Schema Entry Point Discovery
# =============================================================================


class TestComponentRegistrySchemaDiscovery:
    """Test suite for schema entry point discovery behaviour.

    These tests verify that accessing component factories triggers
    schema registration via entry points, ensuring schemas from
    component packages are available before components use them.
    """

    def test_accessing_factories_invokes_schema_entry_points(self) -> None:
        """Schema entry points are invoked when accessing component factories."""
        # Arrange
        container = ServiceContainer()
        registry = ComponentRegistry(container)

        mock_register_func = MagicMock()
        mock_schema_ep = MagicMock()
        mock_schema_ep.name = "test_schema"
        mock_schema_ep.load.return_value = mock_register_func

        with patch("waivern_core.services.registry.entry_points") as mock_entry_points:
            mock_entry_points.side_effect = lambda group: (
                [mock_schema_ep] if group == "waivern.schemas" else []
            )

            # Act - access factories (triggers discovery)
            _ = registry.connector_factories

        # Assert - schema registration function was invoked
        mock_register_func.assert_called_once()

    def test_failed_schema_entry_point_does_not_block_component_discovery(self) -> None:
        """Component discovery succeeds even when schema entry point fails."""
        # Arrange
        container = ServiceContainer()
        registry = ComponentRegistry(container)

        # Schema entry point that raises an exception
        mock_register_func = MagicMock(side_effect=Exception("Schema load failed"))
        mock_schema_ep = MagicMock()
        mock_schema_ep.name = "failing_schema"
        mock_schema_ep.load.return_value = mock_register_func

        # Valid connector factory
        mock_factory_class = MagicMock()
        mock_factory_instance = MagicMock()
        mock_factory_class.return_value = mock_factory_instance

        mock_connector_ep = MagicMock()
        mock_connector_ep.name = "test_connector"
        mock_connector_ep.load.return_value = mock_factory_class

        with patch("waivern_core.services.registry.entry_points") as mock_entry_points:
            mock_entry_points.side_effect = lambda group: {
                "waivern.schemas": [mock_schema_ep],
                "waivern.connectors": [mock_connector_ep],
                "waivern.processors": [],
            }.get(group, [])

            # Act - should succeed despite schema entry point failure
            factories = registry.connector_factories

        # Assert - connector factory discovered successfully
        assert "test_connector" in factories
        assert factories["test_connector"] is mock_factory_instance

    def test_all_schema_entry_points_invoked(self) -> None:
        """All registered schema entry points are invoked during discovery."""
        # Arrange
        container = ServiceContainer()
        registry = ComponentRegistry(container)

        mock_register_func_1 = MagicMock()
        mock_register_func_2 = MagicMock()

        mock_schema_ep_1 = MagicMock()
        mock_schema_ep_1.name = "schema_package_1"
        mock_schema_ep_1.load.return_value = mock_register_func_1

        mock_schema_ep_2 = MagicMock()
        mock_schema_ep_2.name = "schema_package_2"
        mock_schema_ep_2.load.return_value = mock_register_func_2

        with patch("waivern_core.services.registry.entry_points") as mock_entry_points:
            mock_entry_points.side_effect = lambda group: (
                [mock_schema_ep_1, mock_schema_ep_2]
                if group == "waivern.schemas"
                else []
            )

            # Act
            _ = registry.connector_factories

        # Assert - both schema entry points were invoked
        mock_register_func_1.assert_called_once()
        mock_register_func_2.assert_called_once()
