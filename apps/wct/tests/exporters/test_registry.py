"""Tests for ExporterRegistry."""

from unittest.mock import Mock

import pytest


class TestExporterRegistry:
    """Test suite for ExporterRegistry."""

    def test_register_exporter_stores_by_name(self) -> None:
        """Register stores exporter under its name property."""
        from wct.exporters.registry import ExporterRegistry

        # Arrange
        mock_exporter = Mock()
        mock_exporter.name = "test_exporter"

        # Act
        ExporterRegistry.register(mock_exporter)

        # Assert
        retrieved = ExporterRegistry.get("test_exporter")
        assert retrieved is mock_exporter

    def test_get_exporter_returns_registered_instance(self) -> None:
        """Get returns the exact exporter instance that was registered."""
        from wct.exporters.registry import ExporterRegistry

        # Arrange
        mock_exporter = Mock()
        mock_exporter.name = "json"
        ExporterRegistry.register(mock_exporter)

        # Act
        retrieved = ExporterRegistry.get("json")

        # Assert
        assert retrieved is mock_exporter

    def test_get_unknown_exporter_raises_value_error(self) -> None:
        """Get raises ValueError with helpful message for unknown exporter."""
        from wct.exporters.registry import ExporterRegistry

        # Arrange - register some exporters so "available" list is populated
        mock_exporter1 = Mock()
        mock_exporter1.name = "json"
        mock_exporter2 = Mock()
        mock_exporter2.name = "gdpr"
        ExporterRegistry.register(mock_exporter1)
        ExporterRegistry.register(mock_exporter2)

        # Act & Assert
        with pytest.raises(ValueError, match="Unknown exporter 'unknown'"):
            ExporterRegistry.get("unknown")

    def test_list_exporters_returns_all_names(self) -> None:
        """List exporters returns all registered exporter names."""
        from wct.exporters.registry import ExporterRegistry

        # Arrange
        mock_exporter1 = Mock()
        mock_exporter1.name = "json"
        mock_exporter2 = Mock()
        mock_exporter2.name = "gdpr"
        mock_exporter3 = Mock()
        mock_exporter3.name = "ccpa"

        ExporterRegistry.register(mock_exporter1)
        ExporterRegistry.register(mock_exporter2)
        ExporterRegistry.register(mock_exporter3)

        # Act
        names = ExporterRegistry.list_exporters()

        # Assert
        assert set(names) == {"json", "gdpr", "ccpa"}
        assert isinstance(names, list)

    def test_register_duplicate_name_overwrites_previous(self) -> None:
        """Registering same name twice overwrites without error."""
        from wct.exporters.registry import ExporterRegistry

        # Arrange
        mock_exporter1 = Mock()
        mock_exporter1.name = "test"
        mock_exporter2 = Mock()
        mock_exporter2.name = "test"  # Same name

        # Act
        ExporterRegistry.register(mock_exporter1)
        ExporterRegistry.register(mock_exporter2)  # Should overwrite

        # Assert
        retrieved = ExporterRegistry.get("test")
        assert retrieved is mock_exporter2  # Second one wins
        assert retrieved is not mock_exporter1
