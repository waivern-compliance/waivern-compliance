"""Tests for MySQLConnector - Public API Only."""

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest
from waivern_core.errors import ConnectorConfigError, ConnectorExtractionError
from waivern_core.schemas import (
    RelationalDatabaseMetadata,
    Schema,
    StandardInputDataModel,
)

from waivern_mysql import MySQLConnector, MySQLConnectorConfig

# Test constants - expected behaviour from public interface
EXPECTED_CONNECTOR_NAME = "mysql_connector"
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

MYSQL_ENV_VARS = [
    "MYSQL_HOST",
    "MYSQL_PORT",
    "MYSQL_USER",
    "MYSQL_PASSWORD",
    "MYSQL_DATABASE",
]


@pytest.fixture
def clear_mysql_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear MySQL environment variables for test isolation."""
    for var in MYSQL_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def create_mock_cursor(
    tables_data: list[Any],
    columns_data: dict[str, list[Any]],
    table_rows: dict[str, list[Any]],
) -> MagicMock:
    """Create a mock cursor that simulates MySQL query responses.

    Args:
        tables_data: List of (table_name, table_type, comment, row_count) tuples
        columns_data: Dict mapping table_name to list of column tuples
                     (col_name, data_type, is_nullable, default, comment, key, extra)
        table_rows: Dict mapping table_name to list of row tuples

    Returns:
        Mock cursor configured to respond to MySQL queries

    """
    mock_cursor = MagicMock()

    def execute_side_effect(query: str, params: Any = None) -> None:
        # Determine query type and set up appropriate response
        if "information_schema.TABLES" in query:
            # Tables query
            mock_cursor.fetchall.return_value = tables_data
            mock_cursor.description = [
                ("TABLE_NAME",),
                ("TABLE_TYPE",),
                ("TABLE_COMMENT",),
                ("TABLE_ROWS",),
            ]
        elif "information_schema.COLUMNS" in query:
            # Columns query - params[1] is table name
            table_name = params[1] if params and len(params) > 1 else ""
            mock_cursor.fetchall.return_value = columns_data.get(table_name, [])
            mock_cursor.description = [
                ("COLUMN_NAME",),
                ("DATA_TYPE",),
                ("IS_NULLABLE",),
                ("COLUMN_DEFAULT",),
                ("COLUMN_COMMENT",),
                ("COLUMN_KEY",),
                ("EXTRA",),
            ]
        elif "SELECT *" in query:
            # Table data query - extract table name from query
            matched = False
            for table_name, rows in table_rows.items():
                if f"`{table_name}`" in query:
                    mock_cursor.fetchall.return_value = rows
                    # Get column names from columns_data
                    if table_name in columns_data:
                        col_names = [(col[0],) for col in columns_data[table_name]]
                        mock_cursor.description = col_names
                    matched = True
                    break
            if not matched:
                mock_cursor.fetchall.return_value = []
                mock_cursor.description = []

    mock_cursor.execute.side_effect = execute_side_effect
    mock_cursor.__enter__ = Mock(return_value=mock_cursor)
    mock_cursor.__exit__ = Mock(return_value=None)

    return mock_cursor


def create_mock_connection(
    mock_cursor: MagicMock, server_version: str = "8.0.32"
) -> MagicMock:
    """Create a mock MySQL connection.

    Args:
        mock_cursor: The cursor to return from connection.cursor()
        server_version: MySQL server version string

    Returns:
        Mock connection configured for testing

    """
    mock_connection = MagicMock()
    mock_connection.cursor.return_value = mock_cursor
    mock_connection.get_server_info.return_value = server_version
    return mock_connection


@pytest.fixture
def mock_pymysql_connect() -> Generator[MagicMock, None, None]:
    """Fixture that patches pymysql.connect at the module level."""
    with patch("waivern_mysql.connector.pymysql.connect") as mock_connect:
        yield mock_connect


class TestMySQLConnectorPublicAPI:
    """Tests for MySQLConnector focusing only on public API."""

    @pytest.fixture
    def standard_input_schema(self) -> Schema:
        """Return standard input schema."""
        return Schema("standard_input", "1.0.0")

    def test_get_name_returns_correct_name(self) -> None:
        """Test get_name returns the connector name."""
        assert MySQLConnector.get_name() == EXPECTED_CONNECTOR_NAME

    def test_get_supported_output_schemas_returns_standard_input(self) -> None:
        """Test that the connector supports standard_input schema."""
        output_schemas = MySQLConnector.get_supported_output_schemas()

        assert len(output_schemas) == 1
        assert output_schemas[0].name == "standard_input"
        assert output_schemas[0].version == "1.0.0"

    def test_init_with_valid_parameters_succeeds(self, clear_mysql_env: None) -> None:
        """Test initialisation with valid parameters."""
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

    def test_init_raises_error_without_host(self, clear_mysql_env: None) -> None:
        """Test initialisation raises error when host is empty."""
        with pytest.raises(ConnectorConfigError, match="MySQL host is required"):
            config = MySQLConnectorConfig.from_properties(
                {"host": "", "user": TEST_USER}
            )
            MySQLConnector(config)

    def test_init_raises_error_without_user(self, clear_mysql_env: None) -> None:
        """Test initialisation raises error when user is empty."""
        with pytest.raises(ConnectorConfigError, match="MySQL user is required"):
            config = MySQLConnectorConfig.from_properties(
                {"host": TEST_HOST, "user": ""}
            )
            MySQLConnector(config)

    def test_init_with_none_password_converts_to_empty_string(
        self, clear_mysql_env: None
    ) -> None:
        """Test initialisation with None password converts to empty string."""
        config = MySQLConnectorConfig.from_properties(
            {"host": TEST_HOST, "user": TEST_USER, "password": None}
        )
        connector = MySQLConnector(config)
        assert connector is not None

    def test_extract_with_unsupported_schema_raises_error(
        self, clear_mysql_env: None
    ) -> None:
        """Test extract with unsupported schema raises error."""
        config = MySQLConnectorConfig.from_properties(
            {"host": TEST_HOST, "user": TEST_USER}
        )
        connector = MySQLConnector(config)
        mock_schema = Mock()
        mock_schema.name = "unsupported_schema"

        with pytest.raises(ConnectorExtractionError, match="Unsupported output schema"):
            connector.extract(mock_schema)


class TestMySQLConnectorDataExtraction:
    """Tests for MySQL connector data extraction with RelationalDatabaseMetadata."""

    def test_extracts_data_with_relational_database_metadata(
        self, clear_mysql_env: None, mock_pymysql_connect: MagicMock
    ) -> None:
        """Test MySQL connector creates RelationalDatabaseMetadata with accurate database context."""
        # Set up mock database responses
        tables_data = [("customers", "BASE TABLE", "", 1)]
        columns_data = {
            "customers": [
                ("email", "varchar", "YES", None, "", "", ""),
                ("phone", "varchar", "YES", None, "", "", ""),
            ]
        }
        table_rows = {"customers": [("john@test.com", "+1234567890")]}

        mock_cursor = create_mock_cursor(tables_data, columns_data, table_rows)
        mock_connection = create_mock_connection(mock_cursor)
        mock_pymysql_connect.return_value = mock_connection

        # Create connector and extract
        config = MySQLConnectorConfig.from_properties(
            {
                "host": TEST_HOST,
                "user": TEST_USER,
                "password": TEST_PASSWORD,
                "database": TEST_DATABASE,
            }
        )
        connector = MySQLConnector(config)
        result_message = connector.extract(Schema("standard_input", "1.0.0"))

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
        assert email_item.metadata.connector_type == "mysql_connector"
        assert email_item.metadata.table_name == "customers"
        assert email_item.metadata.column_name == "email"
        assert email_item.metadata.schema_name == TEST_DATABASE

        # Test phone metadata
        assert phone_item.metadata.connector_type == "mysql_connector"
        assert phone_item.metadata.table_name == "customers"
        assert phone_item.metadata.column_name == "phone"
        assert phone_item.metadata.schema_name == TEST_DATABASE

    def test_extracts_multiple_tables_with_metadata(
        self, clear_mysql_env: None, mock_pymysql_connect: MagicMock
    ) -> None:
        """Test extraction from multiple tables with proper metadata for each."""
        tables_data = [
            ("customers", "BASE TABLE", "", 1),
            ("orders", "BASE TABLE", "", 1),
        ]
        columns_data = {
            "customers": [
                ("id", "int", "NO", None, "", "PRI", "auto_increment"),
                ("email", "varchar", "YES", None, "", "", ""),
                ("phone", "varchar", "YES", None, "", "", ""),
            ],
            "orders": [
                ("order_id", "int", "NO", None, "", "PRI", "auto_increment"),
                ("customer_id", "int", "NO", None, "", "", ""),
                ("product", "varchar", "YES", None, "", "", ""),
            ],
        }
        table_rows = {
            "customers": [(1, "john@test.com", "+1234567890")],
            "orders": [(100, 1, "Widget A")],
        }

        mock_cursor = create_mock_cursor(tables_data, columns_data, table_rows)
        mock_connection = create_mock_connection(mock_cursor)
        mock_pymysql_connect.return_value = mock_connection

        config = MySQLConnectorConfig.from_properties(
            {
                "host": TEST_HOST,
                "user": TEST_USER,
                "password": TEST_PASSWORD,
                "database": TEST_DATABASE,
            }
        )
        connector = MySQLConnector(config)
        result_message = connector.extract(Schema("standard_input", "1.0.0"))

        typed_result = StandardInputDataModel[
            RelationalDatabaseMetadata
        ].model_validate(result_message.content)

        assert len(typed_result.data) == 6

        customers_items = [
            item
            for item in typed_result.data
            if item.metadata.table_name == "customers"
        ]
        orders_items = [
            item for item in typed_result.data if item.metadata.table_name == "orders"
        ]

        assert len(customers_items) == 3
        assert len(orders_items) == 3
        assert {item.metadata.column_name for item in customers_items} == {
            "id",
            "email",
            "phone",
        }
        assert {item.metadata.column_name for item in orders_items} == {
            "order_id",
            "customer_id",
            "product",
        }
        for item in typed_result.data:
            assert item.metadata.connector_type == "mysql_connector"

    def test_extracts_empty_database_returns_empty_data(
        self, clear_mysql_env: None, mock_pymysql_connect: MagicMock
    ) -> None:
        """Test extraction from database with no tables returns empty data list."""
        # Empty database - no tables
        mock_cursor = create_mock_cursor([], {}, {})
        mock_connection = create_mock_connection(mock_cursor)
        mock_pymysql_connect.return_value = mock_connection

        config = MySQLConnectorConfig.from_properties(
            {
                "host": TEST_HOST,
                "user": TEST_USER,
                "password": TEST_PASSWORD,
                "database": TEST_DATABASE,
            }
        )
        connector = MySQLConnector(config)
        result_message = connector.extract(Schema("standard_input", "1.0.0"))

        typed_result = StandardInputDataModel[
            RelationalDatabaseMetadata
        ].model_validate(result_message.content)
        assert len(typed_result.data) == 0

    def test_extracts_tables_with_special_characters_in_names(
        self, clear_mysql_env: None, mock_pymysql_connect: MagicMock
    ) -> None:
        """Test extraction handles table names with underscores and hyphens."""
        tables_data = [
            ("user_profile", "BASE TABLE", "", 1),
            ("order-items", "BASE TABLE", "", 1),
        ]
        columns_data = {
            "user_profile": [
                ("id", "int", "NO", None, "", "PRI", ""),
                ("name", "varchar", "YES", None, "", "", ""),
            ],
            "order-items": [
                ("id", "int", "NO", None, "", "PRI", ""),
                ("item", "varchar", "YES", None, "", "", ""),
            ],
        }
        table_rows = {
            "user_profile": [(1, "John")],
            "order-items": [(1, "Widget")],
        }

        mock_cursor = create_mock_cursor(tables_data, columns_data, table_rows)
        mock_connection = create_mock_connection(mock_cursor)
        mock_pymysql_connect.return_value = mock_connection

        config = MySQLConnectorConfig.from_properties(
            {
                "host": TEST_HOST,
                "user": TEST_USER,
                "password": TEST_PASSWORD,
                "database": TEST_DATABASE,
            }
        )
        connector = MySQLConnector(config)
        result_message = connector.extract(Schema("standard_input", "1.0.0"))

        typed_result = StandardInputDataModel[
            RelationalDatabaseMetadata
        ].model_validate(result_message.content)

        assert len(typed_result.data) == 4
        assert {item.metadata.table_name for item in typed_result.data} == {
            "user_profile",
            "order-items",
        }
        for item in typed_result.data:
            assert item.metadata.connector_type == "mysql_connector"


class TestMySQLConnectorEdgeCases:
    """Tests for MySQL connector edge cases and error handling."""

    def test_handles_database_with_no_tables(
        self, clear_mysql_env: None, mock_pymysql_connect: MagicMock
    ) -> None:
        """Test handling of valid MySQL database with no user-created tables."""
        mock_cursor = create_mock_cursor([], {}, {})
        mock_connection = create_mock_connection(mock_cursor, "8.0.0-mock")
        mock_pymysql_connect.return_value = mock_connection

        config = MySQLConnectorConfig.from_properties(
            {"host": TEST_HOST, "user": TEST_USER}
        )
        connector = MySQLConnector(config)

        result_message = connector.extract(Schema("standard_input", "1.0.0"))

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

    def test_handles_tables_with_null_values(
        self, clear_mysql_env: None, mock_pymysql_connect: MagicMock
    ) -> None:
        """Test extraction properly handles NULL values in database cells."""
        tables_data = [("users", "BASE TABLE", "", 4)]
        columns_data = {
            "users": [
                ("id", "int", "YES", None, "", "", ""),
                ("name", "varchar", "YES", None, "", "", ""),
                ("email", "varchar", "YES", None, "", "", ""),
            ]
        }
        # Include NULL values in test data
        table_rows = {
            "users": [
                (1, "John", "john@test.com"),
                (2, None, "jane@test.com"),  # NULL name
                (3, "Bob", None),  # NULL email
                (None, None, None),  # All NULL
            ]
        }

        mock_cursor = create_mock_cursor(tables_data, columns_data, table_rows)
        mock_connection = create_mock_connection(mock_cursor)
        mock_pymysql_connect.return_value = mock_connection

        config = MySQLConnectorConfig.from_properties(
            {"host": TEST_HOST, "user": TEST_USER}
        )
        connector = MySQLConnector(config)

        result_message = connector.extract(Schema("standard_input", "1.0.0"))

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
        assert "john@test.com" in contents
        assert "2" in contents
        assert "3" in contents
        assert "Bob" in contents

    def test_returned_message_validates_against_schema(
        self, clear_mysql_env: None, mock_pymysql_connect: MagicMock
    ) -> None:
        """Test that returned Message validates against StandardInputSchema."""
        tables_data = [("test_table", "BASE TABLE", "Test table", 1)]
        columns_data = {"test_table": [("id", "int", "NO", None, "", "PRI", "")]}
        table_rows = {"test_table": [(1,)]}

        mock_cursor = create_mock_cursor(tables_data, columns_data, table_rows)
        mock_connection = create_mock_connection(mock_cursor)
        mock_pymysql_connect.return_value = mock_connection

        config = MySQLConnectorConfig.from_properties(
            {"host": TEST_HOST, "user": TEST_USER}
        )
        connector = MySQLConnector(config)

        result_message = connector.extract(Schema("standard_input", "1.0.0"))

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
        assert len(typed_result.data) == 1  # One data item from mocked record

        # Verify data item structure compliance
        data_item = typed_result.data[0]
        assert hasattr(data_item, "content")
        assert hasattr(data_item, "metadata")
        assert isinstance(data_item.metadata, RelationalDatabaseMetadata)
        assert data_item.metadata.table_name == "test_table"
        assert data_item.metadata.connector_type == "mysql_connector"

    def test_connection_failure_raises_extraction_error(
        self, clear_mysql_env: None, mock_pymysql_connect: MagicMock
    ) -> None:
        """Test that connection failures are wrapped in ConnectorExtractionError."""
        mock_pymysql_connect.side_effect = Exception("Connection refused")

        config = MySQLConnectorConfig.from_properties(
            {"host": TEST_HOST, "user": TEST_USER}
        )
        connector = MySQLConnector(config)

        with pytest.raises(ConnectorExtractionError, match="MySQL connection failed"):
            connector.extract(Schema("standard_input", "1.0.0"))
