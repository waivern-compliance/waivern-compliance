"""Tests for MySQLConnector - Public API Only."""

import os
from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest

from wct.connectors.base import ConnectorConfigError, ConnectorExtractionError
from wct.connectors.mysql.config import MySQLConnectorConfig
from wct.connectors.mysql.connector import MySQLConnector
from wct.schemas import (
    RelationalDatabaseMetadata,
    StandardInputDataModel,
    StandardInputSchema,
)

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


@contextmanager
def clear_mysql_env_vars():
    """Context manager to temporarily clear MySQL environment variables for test isolation."""
    mysql_env_vars = [
        "MYSQL_HOST",
        "MYSQL_PORT",
        "MYSQL_USER",
        "MYSQL_PASSWORD",
        "MYSQL_DATABASE",
    ]
    saved_env = {var: os.environ.pop(var, None) for var in mysql_env_vars}
    try:
        yield
    finally:
        # Restore environment variables
        for var, value in saved_env.items():
            if value is not None:
                os.environ[var] = value


class TestMySQLConnectorPublicAPI:
    """Tests for MySQLConnector focusing only on public API."""

    @pytest.fixture
    def standard_input_schema(self):
        """Standard input schema fixture."""
        return StandardInputSchema()

    def test_get_name_returns_correct_name(self):
        """Test get_name returns the connector name."""
        assert MySQLConnector.get_name() == EXPECTED_CONNECTOR_NAME

    def test_get_supported_output_schemas_returns_standard_input(self):
        """Test that the connector supports standard_input schema."""
        output_schemas = MySQLConnector.get_supported_output_schemas()

        assert len(output_schemas) == 1
        assert output_schemas[0].name == "standard_input"
        assert output_schemas[0].version == "1.0.0"

    def test_from_properties_raises_error_without_host(self):
        """Test from_properties raises error when host is missing."""
        properties = {"user": TEST_USER}

        with clear_mysql_env_vars():
            with pytest.raises(
                ConnectorConfigError, match="MySQL host info is required"
            ):
                MySQLConnector.from_properties(properties)

    def test_from_properties_raises_error_without_user(self):
        """Test from_properties raises error when user is missing."""
        properties = {"host": TEST_HOST}

        with clear_mysql_env_vars():
            with pytest.raises(
                ConnectorConfigError, match="MySQL user info is required"
            ):
                MySQLConnector.from_properties(properties)

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
        with clear_mysql_env_vars():
            config = MySQLConnectorConfig.from_properties(
                {
                    "host": TEST_HOST,
                    "port": TEST_PORT,
                    "user": TEST_USER,
                    "password": TEST_PASSWORD,
                    "database": TEST_DATABASE,
                }
            )
            connector = MySQLConnector(config)
        assert connector is not None

    def test_init_raises_error_without_host(self):
        """Test initialisation raises error when host is empty."""
        with clear_mysql_env_vars():
            with pytest.raises(ConnectorConfigError, match="MySQL host is required"):
                config = MySQLConnectorConfig.from_properties(
                    {"host": "", "user": TEST_USER}
                )
                MySQLConnector(config)

    def test_init_raises_error_without_user(self):
        """Test initialisation raises error when user is empty."""
        with clear_mysql_env_vars():
            with pytest.raises(ConnectorConfigError, match="MySQL user is required"):
                config = MySQLConnectorConfig.from_properties(
                    {"host": TEST_HOST, "user": ""}
                )
                MySQLConnector(config)

    def test_init_with_none_password_converts_to_empty_string(self):
        """Test initialisation with None password converts to empty string."""
        with clear_mysql_env_vars():
            config = MySQLConnectorConfig.from_properties(
                {"host": TEST_HOST, "user": TEST_USER, "password": None}
            )
            connector = MySQLConnector(config)
            assert connector is not None

    def test_extract_without_schema_uses_default(self):
        """Test extract without schema uses default schema."""
        # Test that the validation logic correctly assigns default schema
        with clear_mysql_env_vars():
            config = MySQLConnectorConfig.from_properties(
                {"host": TEST_HOST, "user": TEST_USER}
            )
            connector = MySQLConnector(config)

            # Test the validation method directly since the full extract requires database connection
            result_schema = connector._validate_output_schema(None)
            assert result_schema is not None
            assert result_schema.name == "standard_input"

    def test_extract_with_unsupported_schema_raises_error(self):
        """Test extract with unsupported schema raises error."""
        with clear_mysql_env_vars():
            config = MySQLConnectorConfig.from_properties(
                {"host": TEST_HOST, "user": TEST_USER}
            )
            connector = MySQLConnector(config)
            mock_schema = Mock()
            mock_schema.name = "unsupported_schema"

            with pytest.raises(
                ConnectorExtractionError, match="Unsupported output schema"
            ):
                connector.extract(mock_schema)


class TestMySQLConnectorDataExtraction:
    """Tests for MySQL connector data extraction with RelationalDatabaseMetadata."""

    @pytest.fixture
    def mock_connector_with_data(self):
        """Create a mock connector that returns test database data."""
        with clear_mysql_env_vars():
            config = MySQLConnectorConfig.from_properties(
                {
                    "host": TEST_HOST,
                    "user": TEST_USER,
                    "password": TEST_PASSWORD,
                    "database": TEST_DATABASE,
                }
            )
            connector = MySQLConnector(config)

        # Mock database responses
        with (
            patch.object(connector, "_get_database_metadata") as mock_metadata,
            patch.object(connector, "_get_table_data") as mock_table_data,
        ):
            mock_metadata.return_value = {
                "tables": [
                    {
                        "name": "customers",
                        "columns": [
                            {"COLUMN_NAME": "email", "DATA_TYPE": "varchar"},
                            {"COLUMN_NAME": "phone", "DATA_TYPE": "varchar"},
                        ],
                    }
                ]
            }

            mock_table_data.return_value = [
                {"email": "john@test.com", "phone": "+1234567890"}
            ]

            yield connector

    def test_extracts_data_with_relational_database_metadata(
        self, mock_connector_with_data
    ):
        """Test MySQL connector creates RelationalDatabaseMetadata with accurate database context."""
        result_message = mock_connector_with_data.extract(StandardInputSchema())

        # Validate the result conforms to RelationalDatabaseMetadata expectations
        typed_result = StandardInputDataModel[
            RelationalDatabaseMetadata
        ].model_validate(result_message.content)

        # Should have 2 data items (email + phone from 1 row)
        assert len(typed_result.data) == 2

        # Verify each data item has proper RelationalDatabaseMetadata
        email_item = next(
            item for item in typed_result.data if "john@test.com" in item.content
        )
        phone_item = next(
            item for item in typed_result.data if "+1234567890" in item.content
        )

        # Test email metadata
        assert email_item.metadata.connector_type == "mysql"
        assert email_item.metadata.table_name == "customers"
        assert email_item.metadata.column_name == "email"
        assert email_item.metadata.schema_name == TEST_DATABASE

        # Test phone metadata
        assert phone_item.metadata.connector_type == "mysql"
        assert phone_item.metadata.table_name == "customers"
        assert phone_item.metadata.column_name == "phone"
        assert phone_item.metadata.schema_name == TEST_DATABASE
