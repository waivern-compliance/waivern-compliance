"""Tests for MySQLConnector - Public API Only."""

import os
from typing import cast
from unittest.mock import Mock, patch

import pytest

from wct.connectors.base import ConnectorConfigError, ConnectorExtractionError
from wct.connectors.mysql.connector import MySQLConnector
from wct.schemas import Schema, StandardInputSchema

# Test constants - expected behaviour from public interface
EXPECTED_CONNECTOR_NAME = "mysql"
EXPECTED_DEFAULT_PORT = 3306
EXPECTED_DEFAULT_CHARSET = "utf8mb4"
EXPECTED_DEFAULT_AUTOCOMMIT = True
EXPECTED_DEFAULT_CONNECT_TIMEOUT = 10
EXPECTED_DEFAULT_MAX_ROWS = 10

# Test values
TEST_HOST = "test.mysql.com"
TEST_PORT = 3307
TEST_PORT_ENV = 3309
TEST_USER = "test_user"
TEST_PASSWORD = "test_password"  # noqa: S105
TEST_DATABASE = "test_database"
TEST_CHARSET = "latin1"
TEST_AUTOCOMMIT = False
TEST_CONNECT_TIMEOUT = 20
TEST_MAX_ROWS = 5


class TestMySQLConnectorPublicAPI:
    """Tests for MySQLConnector focusing only on public API."""

    @pytest.fixture
    def standard_input_schema(self):
        """Standard input schema fixture."""
        return StandardInputSchema()

    def test_get_name_returns_correct_name(self):
        """Test get_name returns the connector name."""
        assert MySQLConnector.get_name() == EXPECTED_CONNECTOR_NAME

    def test_from_properties_creates_instance_with_required_properties(self):
        """Test from_properties creates instance with minimum required properties."""
        properties = {
            "host": TEST_HOST,
            "user": TEST_USER,
        }
        connector = MySQLConnector.from_properties(properties)

        assert connector.host == TEST_HOST
        assert connector.port == EXPECTED_DEFAULT_PORT
        assert connector.user == TEST_USER
        assert connector.password == ""
        assert connector.database == ""
        assert connector.charset == EXPECTED_DEFAULT_CHARSET
        assert connector.autocommit == EXPECTED_DEFAULT_AUTOCOMMIT
        assert connector.connect_timeout == EXPECTED_DEFAULT_CONNECT_TIMEOUT
        assert connector.max_rows_per_table == EXPECTED_DEFAULT_MAX_ROWS

    def test_from_properties_creates_instance_with_all_properties(self):
        """Test from_properties creates instance with all properties."""
        properties = {
            "host": TEST_HOST,
            "port": TEST_PORT,
            "user": TEST_USER,
            "password": TEST_PASSWORD,
            "database": TEST_DATABASE,
            "charset": TEST_CHARSET,
            "autocommit": TEST_AUTOCOMMIT,
            "connect_timeout": TEST_CONNECT_TIMEOUT,
            "max_rows_per_table": TEST_MAX_ROWS,
        }
        connector = MySQLConnector.from_properties(properties)

        assert connector.host == TEST_HOST
        assert connector.port == TEST_PORT
        assert connector.user == TEST_USER
        assert connector.password == TEST_PASSWORD
        assert connector.database == TEST_DATABASE
        assert connector.charset == TEST_CHARSET
        assert connector.autocommit == TEST_AUTOCOMMIT
        assert connector.connect_timeout == TEST_CONNECT_TIMEOUT
        assert connector.max_rows_per_table == TEST_MAX_ROWS

    def test_from_properties_raises_error_without_host(self):
        """Test from_properties raises error when host is missing."""
        properties = {"user": TEST_USER}

        with pytest.raises(ConnectorConfigError, match="MySQL host info is required"):
            MySQLConnector.from_properties(properties)

    def test_from_properties_raises_error_without_user(self):
        """Test from_properties raises error when user is missing."""
        properties = {"host": TEST_HOST}

        with pytest.raises(ConnectorConfigError, match="MySQL user info is required"):
            MySQLConnector.from_properties(properties)

    def test_from_properties_uses_environment_variables(self):
        """Test from_properties uses environment variables with priority."""
        properties = {
            "host": "runbook_host",
            "port": 3308,
            "user": "runbook_user",
            "password": "runbook_password",
            "database": "runbook_database",
        }

        env_vars = {
            "MYSQL_HOST": "env_host",
            "MYSQL_PORT": str(TEST_PORT_ENV),
            "MYSQL_USER": "env_user",
            "MYSQL_PASSWORD": "env_password",
            "MYSQL_DATABASE": "env_database",
        }

        with patch.dict(os.environ, env_vars):
            connector = MySQLConnector.from_properties(properties)

        assert connector.host == "env_host"
        assert connector.port == TEST_PORT_ENV
        assert connector.user == "env_user"
        assert connector.password == "env_password"  # noqa: S105
        assert connector.database == "env_database"

    def test_from_properties_handles_invalid_port_env_var(self):
        """Test from_properties raises error for invalid MYSQL_PORT environment variable."""
        properties = {"host": TEST_HOST, "user": TEST_USER}

        with patch.dict(os.environ, {"MYSQL_PORT": "invalid_port"}):
            with pytest.raises(
                ConnectorConfigError, match="Invalid MYSQL_PORT environment variable"
            ):
                MySQLConnector.from_properties(properties)

    def test_init_with_valid_parameters_succeeds(self):
        """Test initialisation with valid parameters."""
        connector = MySQLConnector(
            host=TEST_HOST,
            port=TEST_PORT,
            user=TEST_USER,
            password=TEST_PASSWORD,
            database=TEST_DATABASE,
        )
        assert connector.host == TEST_HOST
        assert connector.port == TEST_PORT
        assert connector.user == TEST_USER
        assert connector.password == TEST_PASSWORD
        assert connector.database == TEST_DATABASE

    def test_init_raises_error_without_host(self):
        """Test initialisation raises error when host is empty."""
        with pytest.raises(ConnectorConfigError, match="MySQL host is required"):
            MySQLConnector(host="", user=TEST_USER)

    def test_init_raises_error_without_user(self):
        """Test initialisation raises error when user is empty."""
        with pytest.raises(ConnectorConfigError, match="MySQL user is required"):
            MySQLConnector(host=TEST_HOST, user="")

    def test_init_with_none_password_converts_to_empty_string(self):
        """Test initialisation with None password converts to empty string."""
        connector = MySQLConnector(host=TEST_HOST, user=TEST_USER, password=None)
        assert connector.password == ""

    def test_extract_without_schema_raises_error(self):
        """Test extract without schema raises error."""
        connector = MySQLConnector(host=TEST_HOST, user=TEST_USER)

        with pytest.raises(ConnectorExtractionError, match="No schema provided"):
            connector.extract(cast("Schema", None))  # type: ignore

    def test_extract_with_unsupported_schema_raises_error(self):
        """Test extract with unsupported schema raises error."""
        connector = MySQLConnector(host=TEST_HOST, user=TEST_USER)
        mock_schema = Mock()
        mock_schema.name = "unsupported_schema"

        with pytest.raises(ConnectorExtractionError, match="Unsupported output schema"):
            connector.extract(mock_schema)

    def test_connector_maintains_connection_parameters(self):
        """Test connector properly maintains all connection parameters."""
        connector = MySQLConnector(
            host=TEST_HOST,
            port=TEST_PORT,
            user=TEST_USER,
            password=TEST_PASSWORD,
            database=TEST_DATABASE,
            charset=TEST_CHARSET,
            autocommit=TEST_AUTOCOMMIT,
            connect_timeout=TEST_CONNECT_TIMEOUT,
            max_rows_per_table=TEST_MAX_ROWS,
        )

        # Verify all parameters are properly stored
        assert connector.host == TEST_HOST
        assert connector.port == TEST_PORT
        assert connector.user == TEST_USER
        assert connector.password == TEST_PASSWORD
        assert connector.database == TEST_DATABASE
        assert connector.charset == TEST_CHARSET
        assert connector.autocommit == TEST_AUTOCOMMIT
        assert connector.connect_timeout == TEST_CONNECT_TIMEOUT
        assert connector.max_rows_per_table == TEST_MAX_ROWS
