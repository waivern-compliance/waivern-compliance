"""Tests for MySQLConnector - Public API Only."""

from collections.abc import Generator
from typing import Any
from unittest.mock import Mock, patch

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

    def test_extract_without_schema_uses_default(self, clear_mysql_env: None) -> None:
        """Test extract without schema uses default schema."""
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
            result_message = connector.extract(Schema("standard_input", "1.0.0"))
            assert result_message.schema is not None
            assert result_message.schema.name == "standard_input"

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

    @pytest.fixture
    def mock_connector_with_data(
        self, clear_mysql_env: None
    ) -> Generator[MySQLConnector, None, None]:
        """Create a mock connector that returns test database data."""
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
        result_message = mock_connector_with_data.extract(
            Schema("standard_input", "1.0.0")
        )

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
        self, clear_mysql_env: None
    ) -> None:
        """Test extraction from multiple tables with proper metadata for each."""
        config = MySQLConnectorConfig.from_properties(
            {
                "host": TEST_HOST,
                "user": TEST_USER,
                "password": TEST_PASSWORD,
                "database": TEST_DATABASE,
            }
        )
        connector = MySQLConnector(config)

        metadata: dict[str, Any] = {
            "database_name": TEST_DATABASE,
            "tables": [
                {
                    "name": "customers",
                    "columns": [
                        {"COLUMN_NAME": "id", "DATA_TYPE": "int"},
                        {"COLUMN_NAME": "email", "DATA_TYPE": "varchar"},
                        {"COLUMN_NAME": "phone", "DATA_TYPE": "varchar"},
                    ],
                },
                {
                    "name": "orders",
                    "columns": [
                        {"COLUMN_NAME": "order_id", "DATA_TYPE": "int"},
                        {"COLUMN_NAME": "customer_id", "DATA_TYPE": "int"},
                        {"COLUMN_NAME": "product", "DATA_TYPE": "varchar"},
                    ],
                },
            ],
            "server_info": {},
        }
        table_rows: dict[str, list[dict[str, object]]] = {
            "customers": [
                {"id": 1, "email": "john@test.com", "phone": "+1234567890"},
            ],
            "orders": [
                {"order_id": 100, "customer_id": 1, "product": "Widget A"},
            ],
        }

        def _table_data(name: str, limit: int | None = None) -> list[dict[str, object]]:
            return table_rows.get(name, [])

        with (
            patch.object(connector, "_get_database_metadata", return_value=metadata),
            patch.object(connector, "_get_table_data") as mock_get_table_data,
        ):
            mock_get_table_data.side_effect = _table_data
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
        self, clear_mysql_env: None
    ) -> None:
        """Test extraction from database with no tables returns empty data list."""
        config = MySQLConnectorConfig.from_properties(
            {
                "host": TEST_HOST,
                "user": TEST_USER,
                "password": TEST_PASSWORD,
                "database": TEST_DATABASE,
            }
        )
        connector = MySQLConnector(config)

        metadata: dict[str, Any] = {
            "database_name": TEST_DATABASE,
            "tables": [],
            "server_info": {},
        }

        with (
            patch.object(connector, "_get_database_metadata", return_value=metadata),
            patch.object(connector, "_get_table_data") as mock_get_table_data,
        ):
            result_message = connector.extract(Schema("standard_input", "1.0.0"))

        typed_result = StandardInputDataModel[
            RelationalDatabaseMetadata
        ].model_validate(result_message.content)
        assert len(typed_result.data) == 0
        mock_get_table_data.assert_not_called()

    def test_extracts_tables_with_special_characters_in_names(
        self, clear_mysql_env: None
    ) -> None:
        """Test extraction handles table names with underscores and hyphens."""
        config = MySQLConnectorConfig.from_properties(
            {
                "host": TEST_HOST,
                "user": TEST_USER,
                "password": TEST_PASSWORD,
                "database": TEST_DATABASE,
            }
        )
        connector = MySQLConnector(config)

        metadata: dict[str, Any] = {
            "database_name": TEST_DATABASE,
            "tables": [
                {
                    "name": "user_profile",
                    "columns": [
                        {"COLUMN_NAME": "id", "DATA_TYPE": "int"},
                        {"COLUMN_NAME": "name", "DATA_TYPE": "varchar"},
                    ],
                },
                {
                    "name": "order-items",
                    "columns": [
                        {"COLUMN_NAME": "id", "DATA_TYPE": "int"},
                        {"COLUMN_NAME": "item", "DATA_TYPE": "varchar"},
                    ],
                },
            ],
            "server_info": {},
        }
        table_rows: dict[str, list[dict[str, object]]] = {
            "user_profile": [{"id": 1, "name": "John"}],
            "order-items": [{"id": 1, "item": "Widget"}],
        }

        def _table_data(name: str, limit: int | None = None) -> list[dict[str, object]]:
            return table_rows.get(name, [])

        with (
            patch.object(connector, "_get_database_metadata", return_value=metadata),
            patch.object(connector, "_get_table_data") as mock_get_table_data,
        ):
            mock_get_table_data.side_effect = _table_data
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

    def test_handles_database_with_no_tables(self, clear_mysql_env: None) -> None:
        """Test handling of valid MySQL database with no user-created tables.

        Business Requirement: MySQL connector must gracefully handle valid databases
        with no user-created tables and return meaningful metadata about the empty result.

        This tests the critical functionality of error handling for empty databases,
        which commonly occurs in fresh installations or system-only databases.
        """
        # Arrange
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

    def test_handles_tables_with_null_values(self, clear_mysql_env: None) -> None:
        """Test extraction properly handles NULL values in database cells.

        Business Requirement: MySQL connector must properly filter NULL database values
        during extraction to ensure only meaningful data is processed for compliance analysis.

        This tests the critical functionality of NULL filtering which directly impacts
        data quality and analysis results in downstream compliance processing.
        """
        # Arrange
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

                result_message = connector.extract(Schema("standard_input", "1.0.0"))

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

    def test_returned_message_validates_against_schema(
        self, clear_mysql_env: None
    ) -> None:
        """Test that returned Message validates against StandardInputSchema.

        Business Requirement: MySQL connector must return data that conforms to the
        StandardInputSchema specification to ensure compatibility with downstream analysers.

        This tests the critical functionality of schema compliance which is mandatory
        for the WCT architecture. Schema validation failures break the entire analysis pipeline.
        """
        # Arrange
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
