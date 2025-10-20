"""Tests for MySQLConnector - Public API Only."""

import os
from collections.abc import Generator
from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest
from waivern_core.errors import ConnectorConfigError, ConnectorExtractionError
from waivern_core.schemas import (
    RelationalDatabaseMetadata,
    StandardInputDataModel,
    StandardInputSchema,
)

from waivern_mysql import MySQLConnector, MySQLConnectorConfig

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
def clear_mysql_env_vars() -> Generator[None, None, None]:
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
    def standard_input_schema(self) -> StandardInputSchema:
        """Return standard input schema."""
        return StandardInputSchema()

    def test_get_name_returns_correct_name(self) -> None:
        """Test get_name returns the connector name."""
        assert MySQLConnector.get_name() == EXPECTED_CONNECTOR_NAME

    def test_get_supported_output_schemas_returns_standard_input(self) -> None:
        """Test that the connector supports standard_input schema."""
        output_schemas = MySQLConnector.get_supported_output_schemas()

        assert len(output_schemas) == 1
        assert output_schemas[0].name == "standard_input"
        assert output_schemas[0].version == "1.0.0"

    def test_from_properties_raises_error_without_host(self) -> None:
        """Test from_properties raises error when host is missing."""
        properties = {"user": TEST_USER}

        with clear_mysql_env_vars():
            with pytest.raises(
                ConnectorConfigError, match="MySQL host info is required"
            ):
                MySQLConnector.from_properties(properties)

    def test_from_properties_raises_error_without_user(self) -> None:
        """Test from_properties raises error when user is missing."""
        properties = {"host": TEST_HOST}

        with clear_mysql_env_vars():
            with pytest.raises(
                ConnectorConfigError, match="MySQL user info is required"
            ):
                MySQLConnector.from_properties(properties)

    def test_from_properties_handles_invalid_port_env_var(self) -> None:
        """Test from_properties raises error for invalid MYSQL_PORT environment variable."""
        properties = {"host": TEST_HOST, "user": TEST_USER}

        with patch.dict(os.environ, {"MYSQL_PORT": "invalid_port"}):
            with pytest.raises(
                ConnectorConfigError, match="Invalid MYSQL_PORT environment variable"
            ):
                MySQLConnector.from_properties(properties)

    def test_init_with_valid_parameters_succeeds(self) -> None:
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

    def test_init_raises_error_without_host(self) -> None:
        """Test initialisation raises error when host is empty."""
        with clear_mysql_env_vars():
            with pytest.raises(ConnectorConfigError, match="MySQL host is required"):
                config = MySQLConnectorConfig.from_properties(
                    {"host": "", "user": TEST_USER}
                )
                MySQLConnector(config)

    def test_init_raises_error_without_user(self) -> None:
        """Test initialisation raises error when user is empty."""
        with clear_mysql_env_vars():
            with pytest.raises(ConnectorConfigError, match="MySQL user is required"):
                config = MySQLConnectorConfig.from_properties(
                    {"host": TEST_HOST, "user": ""}
                )
                MySQLConnector(config)

    def test_init_with_none_password_converts_to_empty_string(self) -> None:
        """Test initialisation with None password converts to empty string."""
        with clear_mysql_env_vars():
            config = MySQLConnectorConfig.from_properties(
                {"host": TEST_HOST, "user": TEST_USER, "password": None}
            )
            connector = MySQLConnector(config)
            assert connector is not None

    def test_extract_without_schema_uses_default(self) -> None:
        """Test extract without schema uses default schema."""
        with clear_mysql_env_vars():
            config = MySQLConnectorConfig.from_properties(
                {"host": TEST_HOST, "user": TEST_USER}
            )
            connector = MySQLConnector(config)

            # Mock the database connection and metadata to test full extract() method
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = []  # Empty table list
            mock_cursor.description = None
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)

            mock_connection = Mock()
            mock_connection.cursor.return_value = mock_cursor
            mock_connection.get_server_info.return_value = "8.0.0-mock"

            with patch.object(connector, "_get_connection") as mock_get_conn:
                mock_get_conn.return_value.__enter__.return_value = mock_connection
                mock_get_conn.return_value.__exit__.return_value = None

                # Extract with StandardInputSchema - should use default
                result_message = connector.extract(StandardInputSchema())
                assert result_message.schema is not None
                assert result_message.schema.name == "standard_input"

    def test_extract_with_unsupported_schema_raises_error(self) -> None:
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
    def mock_connector_with_data(self) -> Generator[MySQLConnector, None, None]:
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
        self, mock_connector_with_data: MySQLConnector
    ) -> None:
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

    def test_extracts_multiple_tables_with_metadata(self) -> None:
        """Test extraction from multiple tables with proper metadata for each."""
        # TODO: Implement to match SQLite connector test pattern
        pass

    def test_extracts_empty_database_returns_empty_data(self) -> None:
        """Test extraction from database with no tables returns empty data list."""
        # TODO: Implement to match SQLite connector test pattern
        pass

    def test_extracts_tables_with_special_characters_in_names(self) -> None:
        """Test extraction handles table names with underscores and hyphens."""
        # TODO: Implement to match SQLite connector test pattern
        pass


class TestMySQLConnectorEdgeCases:
    """Tests for MySQL connector edge cases and error handling."""

    def test_handles_database_with_no_tables(self) -> None:
        """Test handling of valid MySQL database with no user-created tables.

        Business Requirement: MySQL connector must gracefully handle valid databases
        with no user-created tables and return meaningful metadata about the empty result.

        This tests the critical functionality of error handling for empty databases,
        which commonly occurs in fresh installations or system-only databases.
        """
        # Arrange
        with clear_mysql_env_vars():
            config = MySQLConnectorConfig.from_properties(
                {"host": TEST_HOST, "user": TEST_USER}
            )
            connector = MySQLConnector(config)

            # Mock empty database (no tables)
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = []  # Empty table list
            mock_cursor.description = None
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=None)

            mock_connection = Mock()
            mock_connection.cursor.return_value = mock_cursor
            mock_connection.get_server_info.return_value = "8.0.0-mock"

            # Act & Assert
            with patch.object(connector, "_get_connection") as mock_get_conn:
                mock_get_conn.return_value.__enter__.return_value = mock_connection
                mock_get_conn.return_value.__exit__.return_value = None

                result_message = connector.extract(StandardInputSchema())

                # Should succeed with empty data
                assert result_message.schema is not None
                assert result_message.schema.name == "standard_input"
                assert isinstance(result_message.content, dict)

                # Should have empty data list
                data = result_message.content.get("data", [])
                assert len(data) == 0

                # Should have proper metadata indicating no tables processed
                metadata = result_message.content.get("metadata", {})
                extraction_summary = metadata.get("extraction_summary", {})
                assert extraction_summary.get("tables_processed") == 0
                assert extraction_summary.get("cell_values_extracted") == 0

    def test_handles_tables_with_null_values(self) -> None:
        """Test extraction properly handles NULL values in database cells.

        Business Requirement: MySQL connector must properly filter NULL database values
        during extraction to ensure only meaningful data is processed for compliance analysis.

        This tests the critical functionality of NULL filtering which directly impacts
        data quality and analysis results in downstream compliance processing.
        """
        # Arrange
        with clear_mysql_env_vars():
            config = MySQLConnectorConfig.from_properties(
                {"host": TEST_HOST, "user": TEST_USER}
            )
            connector = MySQLConnector(config)

            # For this test, use simplified mocking to test the NULL filtering behavior
            # Mock minimal database metadata that triggers the NULL filtering logic

            # Act & Assert - Use a simpler approach by mocking the entire extraction pipeline
            with patch.object(connector, "_get_database_metadata") as mock_metadata:
                mock_metadata.return_value = {
                    "database_name": "test_db",
                    "tables": [
                        {
                            "name": "users",
                            "type": "BASE TABLE",
                            "comment": "",
                            "estimated_rows": 4,
                            "columns": [],
                        }
                    ],
                    "server_info": {
                        "version": "8.0.0",
                        "host": "localhost",
                        "port": 3306,
                    },
                }

                with patch.object(connector, "_get_table_data") as mock_table_data:
                    # Mock table data with NULL values
                    mock_table_data.return_value = [
                        {"id": 1, "name": "John", "email": "john@test.com"},
                        {"id": 2, "name": None, "email": "jane@test.com"},  # NULL name
                        {"id": 3, "name": "Bob", "email": None},  # NULL email
                        {"id": None, "name": None, "email": None},  # All NULL
                    ]

                    result_message = connector.extract(StandardInputSchema())

                    # Validate the result using proper typing
                    typed_result = StandardInputDataModel[
                        RelationalDatabaseMetadata
                    ].model_validate(result_message.content)

                    # Should only extract non-NULL, non-empty values
                    # Row 1: id(1), name(John), email(john@test.com) = 3 items
                    # Row 2: id(2), email(jane@test.com) = 2 items (NULL name skipped)
                    # Row 3: id(3), name(Bob) = 2 items (NULL email skipped)
                    # Row 4: no items (all NULL)
                    # Total: 7 items
                    assert len(typed_result.data) == 7

                    # Verify NULL values are not included
                    contents = [item.content for item in typed_result.data]
                    assert "None" not in contents
                    assert "" not in contents

                    # Verify non-NULL values are included
                    assert "1" in contents  # id values converted to string
                    assert "John" in contents
                    assert "jane@test.com" in contents
                    assert "2" in contents
                    assert "3" in contents
                    assert "Bob" in contents

    def test_returned_message_validates_against_schema(self) -> None:
        """Test that returned Message validates against StandardInputSchema.

        Business Requirement: MySQL connector must return data that conforms to the
        StandardInputSchema specification to ensure compatibility with downstream analysers.

        This tests the critical functionality of schema compliance which is mandatory
        for the WCT architecture. Schema validation failures break the entire analysis pipeline.
        """
        # Arrange
        with clear_mysql_env_vars():
            config = MySQLConnectorConfig.from_properties(
                {"host": TEST_HOST, "user": TEST_USER}
            )
            connector = MySQLConnector(config)

            # Use simplified mocking approach to test schema validation
            # Act & Assert - Mock high-level components to test schema compliance
            with patch.object(connector, "_get_database_metadata") as mock_metadata:
                mock_metadata.return_value = {
                    "database_name": "test_db",
                    "tables": [
                        {
                            "name": "test_table",
                            "type": "BASE TABLE",
                            "comment": "Test table",
                            "estimated_rows": 1,
                            "columns": [],
                        }
                    ],
                    "server_info": {
                        "version": "8.0.0",
                        "host": "localhost",
                        "port": 3306,
                    },
                }

                with patch.object(connector, "_get_table_data") as mock_table_data:
                    # Mock minimal table data
                    mock_table_data.return_value = [{"id": 1}]

                    result_message = connector.extract(StandardInputSchema())

                    # Assert - Message-level validation
                    result_message.validate()  # Should not raise
                    assert result_message.schema is not None
                    assert result_message.schema.name == "standard_input"
                    assert result_message.schema.version == "1.0.0"

                    # Assert - Content structure validation
                    typed_result = StandardInputDataModel[
                        RelationalDatabaseMetadata
                    ].model_validate(result_message.content)

                    # Verify schema-compliant structure
                    assert typed_result.schemaVersion == "1.0.0"
                    assert typed_result.name is not None
                    assert isinstance(typed_result.data, list)
                    assert (
                        len(typed_result.data) == 1
                    )  # One data item from mocked record

                    # Verify data item structure compliance
                    data_item = typed_result.data[0]
                    assert hasattr(data_item, "content")
                    assert hasattr(data_item, "metadata")
                    assert isinstance(data_item.metadata, RelationalDatabaseMetadata)
                    assert data_item.metadata.table_name == "test_table"
                    assert data_item.metadata.connector_type == "mysql"
