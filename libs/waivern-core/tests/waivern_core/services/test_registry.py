"""Tests for ComponentRegistry - centralised component discovery.

These tests verify the registry's ability to:
- Expose the underlying ServiceContainer
- Lazily discover components from entry points
- Cache discovered factories after first access
"""

from unittest.mock import MagicMock, patch

from waivern_core.services import ComponentRegistry, ServiceContainer


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

            # Assert - entry_points was called for both groups
            assert mock_ep.call_count == 2

    def test_analyser_factories_triggers_discovery(self) -> None:
        """Verify accessing analyser_factories triggers entry point discovery."""
        # Arrange
        container = ServiceContainer()

        with patch("waivern_core.services.registry.entry_points") as mock_ep:
            mock_ep.return_value = []
            registry = ComponentRegistry(container)

            # Act - access analyser_factories
            _ = registry.analyser_factories

            # Assert - entry_points was called for both groups
            assert mock_ep.call_count == 2

    def test_discovery_called_only_once(self) -> None:
        """Verify _discover_components called exactly once despite multiple accesses."""
        # Arrange
        container = ServiceContainer()
        registry = ComponentRegistry(container)

        with patch("waivern_core.services.registry.entry_points") as mock_ep:
            mock_ep.return_value = []

            # Act - access factories multiple times
            _ = registry.connector_factories
            _ = registry.analyser_factories
            _ = registry.connector_factories
            _ = registry.analyser_factories

        # Assert - entry_points called only twice (once per group, single discovery)
        assert mock_ep.call_count == 2

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

    def test_discovered_analyser_factory_accessible_by_name(self) -> None:
        """Verify discovered analyser factories are accessible by entry point name."""
        # Arrange
        container = ServiceContainer()
        registry = ComponentRegistry(container)

        mock_factory_class = MagicMock()
        mock_factory_instance = MagicMock()
        mock_factory_class.return_value = mock_factory_instance

        mock_ep = MagicMock()
        mock_ep.name = "test_analyser"
        mock_ep.load.return_value = mock_factory_class

        with patch("waivern_core.services.registry.entry_points") as mock_entry_points:
            mock_entry_points.side_effect = lambda group: (
                [mock_ep] if group == "waivern.analysers" else []
            )

            # Act
            factories = registry.analyser_factories

        # Assert
        assert "test_analyser" in factories
        assert factories["test_analyser"] is mock_factory_instance

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
