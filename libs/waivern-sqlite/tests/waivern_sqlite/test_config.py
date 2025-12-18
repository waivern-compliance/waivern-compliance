"""Tests for SQLite connector configuration."""

import pytest
from waivern_core.errors import ConnectorConfigError

from waivern_sqlite.config import SQLiteConnectorConfig


class TestSQLiteConfig:
    """Test SQLite connector configuration validation."""

    def test_sqlite_config_validates_database_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SQLite config requires valid database file path."""
        monkeypatch.delenv("SQLITE_DATABASE_PATH", raising=False)

        # Arrange & Act & Assert - Empty path should fail
        with pytest.raises(ConnectorConfigError, match="database_path is required"):
            SQLiteConnectorConfig.from_properties({})

        # Arrange & Act & Assert - None path should fail
        with pytest.raises(ConnectorConfigError, match="database_path is required"):
            SQLiteConnectorConfig.from_properties({"database_path": None})

        # Arrange & Act & Assert - Empty string should fail
        with pytest.raises(ConnectorConfigError, match="database_path is required"):
            SQLiteConnectorConfig.from_properties({"database_path": ""})

    def test_sqlite_config_validates_max_rows_per_table(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SQLite config ensures row limit is positive integer."""
        monkeypatch.delenv("SQLITE_DATABASE_PATH", raising=False)

        # Arrange & Act & Assert - Zero rows should fail
        with pytest.raises(
            ConnectorConfigError, match="Input should be greater than 0"
        ):
            SQLiteConnectorConfig.from_properties(
                {"database_path": "/path/to/test.db", "max_rows_per_table": 0}
            )

        # Arrange & Act & Assert - Negative rows should fail
        with pytest.raises(
            ConnectorConfigError, match="Input should be greater than 0"
        ):
            SQLiteConnectorConfig.from_properties(
                {"database_path": "/path/to/test.db", "max_rows_per_table": -5}
            )

        # Arrange & Act & Assert - Valid positive value should pass
        config = SQLiteConnectorConfig.from_properties(
            {"database_path": "/path/to/test.db", "max_rows_per_table": 50}
        )
        assert config.max_rows_per_table == 50

    def test_sqlite_config_provides_defaults(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SQLite config uses sensible defaults for optional parameters."""
        monkeypatch.delenv("SQLITE_DATABASE_PATH", raising=False)

        # Arrange & Act - Only provide required parameter
        config = SQLiteConnectorConfig.from_properties(
            {"database_path": "/path/to/test.db"}
        )

        # Assert - Defaults are applied
        assert config.database_path == "/path/to/test.db"
        assert config.max_rows_per_table == 10  # Default value

    def test_sqlite_config_environment_variable_overrides_properties(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SQLITE_DATABASE_PATH environment variable takes precedence over runbook properties."""
        monkeypatch.setenv("SQLITE_DATABASE_PATH", "/env/override/test.db")

        # Act - Create config with different path in properties
        config = SQLiteConnectorConfig.from_properties(
            {"database_path": "/runbook/path/test.db", "max_rows_per_table": 25}
        )

        # Assert - Environment variable takes precedence
        assert config.database_path == "/env/override/test.db"
        assert config.max_rows_per_table == 25  # Other properties still work
