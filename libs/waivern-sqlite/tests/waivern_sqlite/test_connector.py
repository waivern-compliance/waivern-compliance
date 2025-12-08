"""Tests for SQLite connector functionality."""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest
from waivern_core.errors import ConnectorExtractionError
from waivern_core.schemas import (
    RelationalDatabaseMetadata,
    Schema,
    StandardInputDataModel,
)

from waivern_sqlite.config import SQLiteConnectorConfig
from waivern_sqlite.connector import SQLiteConnector


class TestSQLiteConnector:
    """Test SQLite connector core functionality."""

    def test_sqlite_connector_connects_to_file_database(self):
        """SQLite connector establishes connection using file path."""
        # Arrange - Create temporary SQLite database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            temp_db_path = temp_db.name

        try:
            # Act - Create connector from properties
            config = SQLiteConnectorConfig.from_properties(
                {"database_path": temp_db_path}
            )
            connector = SQLiteConnector(config)

            # Assert - Connector is created successfully
            assert connector is not None
            assert connector.get_name() == "sqlite_connector"

            # Assert - Supports standard_input schema
            schemas = connector.get_supported_output_schemas()
            assert len(schemas) == 1
            assert schemas[0].name == "standard_input"

        finally:
            # Clean up temporary file
            Path(temp_db_path).unlink(missing_ok=True)

    def test_sqlite_connector_extracts_table_data_with_row_limit(self):
        """SQLite connector respects max_rows_per_table configuration."""
        # Arrange - Create temporary SQLite database with test data

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            temp_db_path = temp_db.name

        try:
            # Create test database with sample data
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()

            # Create table with test data
            cursor.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    email TEXT
                )
            """)

            # Insert more rows than the limit to test row limiting
            test_data = [
                (1, "John Doe", "john@example.com"),
                (2, "Jane Smith", "jane@example.com"),
                (3, "Bob Johnson", "bob@example.com"),
                (4, "Alice Brown", "alice@example.com"),
                (5, "Charlie Wilson", "charlie@example.com"),
            ]
            cursor.executemany("INSERT INTO users VALUES (?, ?, ?)", test_data)
            conn.commit()
            conn.close()

            # Act - Create connector with row limit of 2
            config = SQLiteConnectorConfig.from_properties(
                {"database_path": temp_db_path, "max_rows_per_table": 2}
            )
            connector = SQLiteConnector(config)

            schema = Schema("standard_input", "1.0.0")
            message = connector.extract(schema)

            # Assert - Should respect row limit
            assert (
                message.schema is not None and message.schema.name == "standard_input"
            )
            assert isinstance(message.content, dict)

            # Should have limited number of rows per table
            data = message.content.get("data", [])
            # Filter data from users table (look for table_name in metadata)
            users_data = [
                item
                for item in data
                if item.get("metadata", {}).get("table_name") == "users"
            ]
            # With 2 rows and 3 columns (id, name, email), expect 6 data items
            expected_items = 2 * 3  # max_rows_per_table * column_count
            assert len(users_data) == expected_items

            # Verify we got the first 2 rows (check for ID values 1 and 2 in content)
            id_values = [
                item["content"]
                for item in users_data
                if item.get("metadata", {}).get("column_name") == "id"
            ]
            id_values = sorted(
                [int(val) for val in id_values if val and str(val).isdigit()]
            )
            assert id_values == [1, 2]

        finally:
            # Clean up
            Path(temp_db_path).unlink(missing_ok=True)

    def test_sqlite_connector_handles_missing_database_file(self):
        """SQLite connector raises appropriate error when database file doesn't exist."""
        # Arrange - Create connector with non-existent database path
        config = SQLiteConnectorConfig.from_properties(
            {"database_path": "/nonexistent/path/database.db"}
        )
        connector = SQLiteConnector(config)

        # Act & Assert - Extraction should raise appropriate error
        schema = Schema("standard_input", "1.0.0")
        with pytest.raises(ConnectorExtractionError, match="database file not found"):
            connector.extract(schema)

    def test_sqlite_connector_handles_corrupted_database(self):
        """SQLite connector raises appropriate error for invalid SQLite files."""
        # Arrange - Create a file with invalid SQLite content
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
            # Write non-SQLite content to simulate corruption
            temp_file.write(b"This is not a valid SQLite database file")
            temp_file_path = temp_file.name

        try:
            # Act - Create connector with corrupted database file
            config = SQLiteConnectorConfig.from_properties(
                {"database_path": temp_file_path}
            )
            connector = SQLiteConnector(config)

            # Act & Assert - Extraction should raise appropriate error
            schema = Schema("standard_input", "1.0.0")
            with pytest.raises(
                ConnectorExtractionError, match="file is not a database"
            ):
                connector.extract(schema)

        finally:
            # Clean up
            Path(temp_file_path).unlink(missing_ok=True)


class TestSQLiteConnectorPublicAPI:
    """Tests for SQLite connector public API following MySQL connector patterns."""

    @pytest.fixture
    def standard_input_schema(self):
        """Standard input schema fixture."""
        return Schema("standard_input", "1.0.0")

    def test_get_name_returns_correct_name(self):
        """Test get_name returns the connector name."""
        assert SQLiteConnector.get_name() == "sqlite_connector"

    def test_get_supported_output_schemas_returns_standard_input(self):
        """Test that the connector supports standard_input schema."""
        output_schemas = SQLiteConnector.get_supported_output_schemas()

        assert len(output_schemas) == 1
        assert output_schemas[0].name == "standard_input"
        assert output_schemas[0].version == "1.0.0"

    def test_extract_without_schema_uses_default(self):
        """Test extract without schema uses default schema."""
        # Create a temporary empty database for testing
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            temp_db_path = temp_db.name

        try:
            # Create empty database
            conn = sqlite3.connect(temp_db_path)
            conn.close()

            # Create connector
            config = SQLiteConnectorConfig.from_properties(
                {"database_path": temp_db_path}
            )
            connector = SQLiteConnector(config)

            # Extract with None schema - should use default
            result_message = connector.extract(None)  # type: ignore[arg-type]
            assert result_message.schema is not None
            assert result_message.schema.name == "standard_input"

        finally:
            Path(temp_db_path).unlink(missing_ok=True)

    def test_extract_with_unsupported_schema_raises_error(self):
        """Test extract with unsupported schema raises error."""
        # Create a temporary empty database for testing
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            temp_db_path = temp_db.name

        try:
            # Create empty database
            conn = sqlite3.connect(temp_db_path)
            conn.close()

            # Create connector
            config = SQLiteConnectorConfig.from_properties(
                {"database_path": temp_db_path}
            )
            connector = SQLiteConnector(config)

            # Create mock unsupported schema
            mock_schema = Mock()
            mock_schema.name = "unsupported_schema"

            with pytest.raises(
                ConnectorExtractionError, match="Unsupported output schema"
            ):
                connector.extract(mock_schema)

        finally:
            Path(temp_db_path).unlink(missing_ok=True)


class TestSQLiteConnectorDataExtraction:
    """Tests for SQLite connector data extraction with RelationalDatabaseMetadata."""

    @pytest.fixture
    def mock_connector_with_single_table(self):
        """Create a connector with single table test data."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            temp_db_path = temp_db.name

        # Create test database with single table
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # Create customers table
        cursor.execute("""
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY,
                email TEXT,
                phone TEXT
            )
        """)

        # Insert test data
        cursor.execute(
            "INSERT INTO customers VALUES (1, 'john@test.com', '+1234567890')"
        )
        conn.commit()
        conn.close()

        # Create connector
        config = SQLiteConnectorConfig.from_properties({"database_path": temp_db_path})
        connector = SQLiteConnector(config)

        yield connector

        # Cleanup
        Path(temp_db_path).unlink(missing_ok=True)

    @pytest.fixture
    def mock_connector_with_multiple_tables(self):
        """Create a connector with multiple table test data."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            temp_db_path = temp_db.name

        # Create test database with multiple tables
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # Create customers table
        cursor.execute("""
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY,
                email TEXT,
                phone TEXT
            )
        """)

        # Create orders table
        cursor.execute("""
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                product TEXT
            )
        """)

        # Insert test data
        cursor.execute(
            "INSERT INTO customers VALUES (1, 'john@test.com', '+1234567890')"
        )
        cursor.execute("INSERT INTO orders VALUES (100, 1, 'Widget A')")
        conn.commit()
        conn.close()

        # Create connector
        config = SQLiteConnectorConfig.from_properties({"database_path": temp_db_path})
        connector = SQLiteConnector(config)

        yield connector

        # Cleanup
        Path(temp_db_path).unlink(missing_ok=True)

    def test_extracts_data_with_relational_database_metadata(
        self, mock_connector_with_single_table
    ):
        """Test SQLite connector creates RelationalDatabaseMetadata with accurate database context."""
        result_message = mock_connector_with_single_table.extract(
            Schema("standard_input", "1.0.0")
        )

        # Validate the result conforms to RelationalDatabaseMetadata expectations
        typed_result = StandardInputDataModel[
            RelationalDatabaseMetadata
        ].model_validate(result_message.content)

        # Should have 3 data items (id + email + phone from 1 row)
        assert len(typed_result.data) == 3

        # Verify each data item has proper RelationalDatabaseMetadata
        email_item = next(
            item for item in typed_result.data if "john@test.com" in item.content
        )
        phone_item = next(
            item for item in typed_result.data if "+1234567890" in item.content
        )
        id_item = next(item for item in typed_result.data if "1" == item.content)

        # Test email metadata
        assert email_item.metadata.connector_type == "sqlite_connector"
        assert email_item.metadata.table_name == "customers"
        assert email_item.metadata.column_name == "email"
        # SQLite uses filename stem as schema_name
        assert email_item.metadata.schema_name.startswith("tmp")  # temp file name

        # Test phone metadata
        assert phone_item.metadata.connector_type == "sqlite_connector"
        assert phone_item.metadata.table_name == "customers"
        assert phone_item.metadata.column_name == "phone"

        # Test id metadata
        assert id_item.metadata.connector_type == "sqlite_connector"
        assert id_item.metadata.table_name == "customers"
        assert id_item.metadata.column_name == "id"

    def test_extracts_multiple_tables_with_metadata(
        self, mock_connector_with_multiple_tables
    ):
        """Test extraction from multiple tables with proper metadata for each."""
        result_message = mock_connector_with_multiple_tables.extract(
            Schema("standard_input", "1.0.0")
        )

        # Validate the result conforms to RelationalDatabaseMetadata expectations
        typed_result = StandardInputDataModel[
            RelationalDatabaseMetadata
        ].model_validate(result_message.content)

        # Should have 6 data items (3 from customers + 3 from orders)
        assert len(typed_result.data) == 6

        # Group data items by table
        customers_items = [
            item
            for item in typed_result.data
            if item.metadata.table_name == "customers"
        ]
        orders_items = [
            item for item in typed_result.data if item.metadata.table_name == "orders"
        ]

        # Should have 3 items from each table
        assert len(customers_items) == 3
        assert len(orders_items) == 3

        # Verify customers table items
        customer_columns = {item.metadata.column_name for item in customers_items}
        assert customer_columns == {"id", "email", "phone"}

        # Verify orders table items
        order_columns = {item.metadata.column_name for item in orders_items}
        assert order_columns == {"order_id", "customer_id", "product"}

        # Verify all items have correct connector type
        for item in typed_result.data:
            assert item.metadata.connector_type == "sqlite_connector"

    def test_extracts_empty_database_returns_empty_data(self):
        """Test extraction from database with no tables returns empty data list."""
        # Create empty database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            temp_db_path = temp_db.name

        try:
            # Create empty database (no tables)
            conn = sqlite3.connect(temp_db_path)
            conn.close()

            # Create connector
            config = SQLiteConnectorConfig.from_properties(
                {"database_path": temp_db_path}
            )
            connector = SQLiteConnector(config)
            result_message = connector.extract(Schema("standard_input", "1.0.0"))

            # Validate the result conforms to RelationalDatabaseMetadata expectations
            typed_result = StandardInputDataModel[
                RelationalDatabaseMetadata
            ].model_validate(result_message.content)

            # Should have 0 data items (empty database)
            assert len(typed_result.data) == 0

        finally:
            Path(temp_db_path).unlink(missing_ok=True)

    def test_extracts_tables_with_special_characters_in_names(self):
        """Test extraction handles table names with underscores and hyphens.

        Validates that the security filtering allows legitimate table names containing
        underscores and hyphens while the connector extracts data successfully.
        """
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            temp_db_path = temp_db.name

        try:
            # Create test database with table names containing underscores and hyphens
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()

            # Create valid table names with underscores and hyphens
            cursor.execute("CREATE TABLE user_profile (id INTEGER, name TEXT)")
            cursor.execute("CREATE TABLE `order-items` (id INTEGER, item TEXT)")

            # Insert test data
            cursor.execute("INSERT INTO user_profile VALUES (1, 'John')")
            cursor.execute("INSERT INTO `order-items` VALUES (1, 'Widget')")
            conn.commit()
            conn.close()

            # Create connector
            config = SQLiteConnectorConfig.from_properties(
                {"database_path": temp_db_path}
            )
            connector = SQLiteConnector(config)
            result_message = connector.extract(Schema("standard_input", "1.0.0"))

            # Validate the result
            typed_result = StandardInputDataModel[
                RelationalDatabaseMetadata
            ].model_validate(result_message.content)

            # Should have 4 data items (2 tables × 2 columns each)
            assert len(typed_result.data) == 4

            # Verify table names are properly handled
            table_names = {item.metadata.table_name for item in typed_result.data}
            assert table_names == {"user_profile", "order-items"}

        finally:
            Path(temp_db_path).unlink(missing_ok=True)


class TestSQLiteConnectorEdgeCases:
    """Tests for SQLite connector edge cases and error handling."""

    def test_handles_database_with_no_tables(self):
        """Test handling of valid SQLite database with no user-created tables."""
        # Create empty database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            temp_db_path = temp_db.name

        try:
            # Create empty database (no tables)
            conn = sqlite3.connect(temp_db_path)
            conn.close()

            # Create connector
            config = SQLiteConnectorConfig.from_properties(
                {"database_path": temp_db_path}
            )
            connector = SQLiteConnector(config)
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

        finally:
            Path(temp_db_path).unlink(missing_ok=True)

    def test_handles_tables_with_null_values(self):
        """Test extraction properly handles NULL values in database cells."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            temp_db_path = temp_db.name

        try:
            # Create test database with NULL values
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE users (
                    id INTEGER,
                    name TEXT,
                    email TEXT
                )
            """)

            # Insert data with NULL values
            cursor.execute("INSERT INTO users VALUES (1, 'John', 'john@test.com')")
            cursor.execute(
                "INSERT INTO users VALUES (2, NULL, 'jane@test.com')"
            )  # NULL name
            cursor.execute("INSERT INTO users VALUES (3, 'Bob', NULL)")  # NULL email
            cursor.execute("INSERT INTO users VALUES (NULL, NULL, NULL)")  # All NULL
            conn.commit()
            conn.close()

            # Create connector
            config = SQLiteConnectorConfig.from_properties(
                {"database_path": temp_db_path}
            )
            connector = SQLiteConnector(config)
            result_message = connector.extract(Schema("standard_input", "1.0.0"))

            # Validate the result
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
            assert "John" in contents
            assert "jane@test.com" in contents
            assert "Bob" in contents

        finally:
            Path(temp_db_path).unlink(missing_ok=True)

    def test_skips_tables_with_unsafe_names(self):
        """Test security validation skips tables with non-alphanumeric characters."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            temp_db_path = temp_db.name

        try:
            # Create test database with various table names
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()

            # Create safe table (should be processed)
            cursor.execute("CREATE TABLE safe_table (id INTEGER, data TEXT)")
            cursor.execute("INSERT INTO safe_table VALUES (1, 'safe')")

            # Create unsafe table names (should be skipped)
            # Note: These are examples - in practice, SQLite allows these but our connector skips them for security
            cursor.execute("CREATE TABLE `table with spaces` (id INTEGER)")
            cursor.execute("INSERT INTO `table with spaces` VALUES (1)")

            cursor.execute("CREATE TABLE `table;drop` (id INTEGER)")
            cursor.execute("INSERT INTO `table;drop` VALUES (1)")

            conn.commit()
            conn.close()

            # Create connector
            config = SQLiteConnectorConfig.from_properties(
                {"database_path": temp_db_path}
            )
            connector = SQLiteConnector(config)
            result_message = connector.extract(Schema("standard_input", "1.0.0"))

            # Validate the result
            typed_result = StandardInputDataModel[
                RelationalDatabaseMetadata
            ].model_validate(result_message.content)

            # Should only extract from safe_table (2 data items: id + data)
            assert len(typed_result.data) == 2

            # Verify only safe table is processed
            table_names = {item.metadata.table_name for item in typed_result.data}
            assert table_names == {"safe_table"}

            # Verify unsafe tables are not processed
            assert "table with spaces" not in table_names
            assert "table;drop" not in table_names

            # Verify safe data is extracted
            contents = [item.content for item in typed_result.data]
            assert "safe" in contents
            assert "1" in contents

        finally:
            Path(temp_db_path).unlink(missing_ok=True)

    def test_returned_message_validates_against_schema(self):
        """Test that returned Message validates against StandardInputSchema."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            temp_db_path = temp_db.name

        try:
            # Create test database with data
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE test_table (id INTEGER, data TEXT)")
            cursor.execute("INSERT INTO test_table VALUES (1, 'test')")
            conn.commit()
            conn.close()

            # Create connector
            config = SQLiteConnectorConfig.from_properties(
                {"database_path": temp_db_path}
            )
            connector = SQLiteConnector(config)
            result_message = connector.extract(Schema("standard_input", "1.0.0"))

            # Should validate against StandardInputSchema
            assert result_message.schema is not None
            assert result_message.schema.name == "standard_input"

            # Content should be valid standard_input format
            assert "schemaVersion" in result_message.content
            assert "data" in result_message.content
            assert "metadata" in result_message.content

            # Data should be a list of items with RelationalDatabaseMetadata
            data_items = result_message.content["data"]
            assert isinstance(data_items, list)

            for item in data_items:
                assert "content" in item
                assert "metadata" in item
                # Metadata should have RelationalDatabaseMetadata structure
                metadata = item["metadata"]
                assert "connector_type" in metadata
                assert "table_name" in metadata
                assert "column_name" in metadata
                assert "schema_name" in metadata

        finally:
            Path(temp_db_path).unlink(missing_ok=True)

    def test_message_content_structure_matches_standard_input(self):
        """Test message content structure conforms to standard_input schema."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            temp_db_path = temp_db.name

        try:
            # Create test database with data
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE users (id INTEGER, name TEXT)")
            cursor.execute("INSERT INTO users VALUES (1, 'Alice')")
            conn.commit()
            conn.close()

            # Create connector
            config = SQLiteConnectorConfig.from_properties(
                {"database_path": temp_db_path}
            )
            connector = SQLiteConnector(config)
            result_message = connector.extract(Schema("standard_input", "1.0.0"))

            # Verify top-level structure matches standard_input schema
            content = result_message.content

            # Required top-level fields
            assert content["schemaVersion"] == "1.0.0"
            assert content["name"].startswith("sqlite_text_from_")
            assert "description" in content
            assert content["contentEncoding"] == "utf-8"
            assert "source" in content

            # Metadata structure
            metadata = content["metadata"]
            assert metadata["connector_type"] == "sqlite_connector"
            assert "connection_info" in metadata
            assert "database_schema" in metadata
            assert "total_data_items" in metadata
            assert "extraction_summary" in metadata

            # Data structure - should be list of StandardInputDataModel items
            data = content["data"]
            assert isinstance(data, list)
            assert len(data) == 2  # id + name

            # Each data item should have correct structure
            for item in data:
                assert "content" in item
                assert "metadata" in item
                assert isinstance(item["content"], str)
                assert isinstance(item["metadata"], dict)

        finally:
            Path(temp_db_path).unlink(missing_ok=True)
