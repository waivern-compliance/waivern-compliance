"""Tests for MySQLConnectorConfig."""

import os
from unittest.mock import patch

import pytest
from waivern_core.errors import ConnectorConfigError

from wct.connectors.mysql.config import MySQLConnectorConfig


@pytest.fixture
def clear_mysql_env_vars():
    """Clear MySQL environment variables for testing."""
    env_vars_to_clear = [
        "MYSQL_HOST",
        "MYSQL_PORT",
        "MYSQL_USER",
        "MYSQL_PASSWORD",
        "MYSQL_DATABASE",
    ]

    # Store original values
    original_values = {}
    for var in env_vars_to_clear:
        if var in os.environ:
            original_values[var] = os.environ[var]
            del os.environ[var]

    yield

    # Restore original values
    for var, value in original_values.items():
        os.environ[var] = value


class TestMySQLConnectorConfig:
    """Test MySQLConnectorConfig class."""

    def test_from_properties_with_minimal_config(self, clear_mysql_env_vars):
        """Test from_properties applies correct defaults with minimal config."""
        config = MySQLConnectorConfig.from_properties(
            {
                "host": "localhost",
                "user": "testuser",
            }
        )

        assert config.host == "localhost"
        assert config.port == 3306  # Default
        assert config.user == "testuser"
        assert config.password == ""  # Default
        assert config.database == ""  # Default
        assert config.charset == "utf8mb4"  # Default
        assert config.autocommit is True  # Default
        assert config.connect_timeout == 10  # Default
        assert config.max_rows_per_table == 10  # Default

    def test_from_properties_with_full_config(self, clear_mysql_env_vars):
        """Test from_properties respects all provided properties."""
        config = MySQLConnectorConfig.from_properties(
            {
                "host": "testhost",
                "port": 3307,
                "user": "testuser",
                "password": "testpass",
                "database": "testdb",
                "charset": "latin1",
                "autocommit": False,
                "connect_timeout": 30,
                "max_rows_per_table": 2000,
            }
        )

        assert config.host == "testhost"
        assert config.port == 3307
        assert config.user == "testuser"
        assert config.password == "testpass"  # noqa: S105
        assert config.database == "testdb"
        assert config.charset == "latin1"
        assert config.autocommit is False
        assert config.connect_timeout == 30
        assert config.max_rows_per_table == 2000

    def test_from_properties_uses_environment_variables(self):
        """Test from_properties uses environment variables with priority over properties."""
        properties = {
            "host": "runbook_host",
            "port": 3308,
            "user": "runbook_user",
            "password": "runbook_password",
            "database": "runbook_database",
        }

        env_vars = {
            "MYSQL_HOST": "env_host",
            "MYSQL_PORT": "3309",
            "MYSQL_USER": "env_user",
            "MYSQL_PASSWORD": "env_password",
            "MYSQL_DATABASE": "env_database",
        }

        with patch.dict(os.environ, env_vars):
            config = MySQLConnectorConfig.from_properties(properties)

        assert config.host == "env_host"
        assert config.port == 3309
        assert config.user == "env_user"
        assert config.password == "env_password"  # noqa: S105
        assert config.database == "env_database"

    def test_from_properties_missing_host_raises_error(self, clear_mysql_env_vars):
        """Test from_properties raises error when host is missing."""
        with pytest.raises(ConnectorConfigError, match="MySQL host info is required"):
            MySQLConnectorConfig.from_properties({"user": "testuser"})

    def test_from_properties_missing_user_raises_error(self, clear_mysql_env_vars):
        """Test from_properties raises error when user is missing."""
        with pytest.raises(ConnectorConfigError, match="MySQL user info is required"):
            MySQLConnectorConfig.from_properties({"host": "localhost"})

    def test_from_properties_invalid_port_env_var_raises_error(
        self, clear_mysql_env_vars
    ):
        """Test from_properties raises error for invalid MYSQL_PORT environment variable."""
        properties = {"host": "localhost", "user": "testuser"}

        with patch.dict(os.environ, {"MYSQL_PORT": "invalid_port"}):
            with pytest.raises(
                ConnectorConfigError, match="Invalid MYSQL_PORT environment variable"
            ):
                MySQLConnectorConfig.from_properties(properties)

    def test_none_password_converts_to_empty_string(self, clear_mysql_env_vars):
        """Test that None password is converted to empty string."""
        config = MySQLConnectorConfig.from_properties(
            {"host": "localhost", "user": "testuser", "password": None}
        )

        assert config.password == ""
