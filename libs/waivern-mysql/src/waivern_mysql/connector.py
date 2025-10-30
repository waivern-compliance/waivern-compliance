"""MySQL database connector for WCT compliance data extraction.

This module provides:
- MySQLConnector: Main connector class for MySQL database integration
- Support for extracting database metadata and content
- Transformation capabilities for standard_input schema
- Connection management with proper error handling and logging
"""

import logging
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, Self, override

import pymysql
from waivern_connectors_database import (
    DatabaseExtractionUtils,
    DatabaseSchemaUtils,
)
from waivern_core.base_connector import Connector
from waivern_core.errors import (
    ConnectorExtractionError,
)
from waivern_core.message import Message
from waivern_core.schemas import (
    RelationalDatabaseMetadata,
    Schema,
    StandardInputSchema,
)

from waivern_mysql.config import MySQLConnectorConfig

logger = logging.getLogger(__name__)

# Constants
_CONNECTOR_NAME = "mysql_connector"

# SQL Queries
_TABLES_QUERY = """
SELECT TABLE_NAME, TABLE_TYPE, TABLE_COMMENT, TABLE_ROWS
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = %s
ORDER BY TABLE_NAME
"""

_COLUMNS_QUERY = """
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT,
       COLUMN_COMMENT, COLUMN_KEY, EXTRA
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
ORDER BY ORDINAL_POSITION
"""

_SUPPORTED_OUTPUT_SCHEMAS: list[Schema] = [StandardInputSchema()]


class MySQLConnector(Connector):
    """MySQL database connector for extracting data and metadata.

    This connector connects to a MySQL database and can execute queries
    to extract data and transform it into supported Schema formats
    for compliance analysis.
    """

    def __init__(self, config: MySQLConnectorConfig) -> None:
        """Initialise MySQL connector with validated configuration.

        Args:
            config: Validated MySQL connector configuration

        """
        self._config = config

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the connector."""
        return _CONNECTOR_NAME

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Return the output schemas supported by this connector."""
        return _SUPPORTED_OUTPUT_SCHEMAS

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create connector from properties (legacy method for Executor compatibility).

        TODO: Remove this method in Phase 6 when Executor uses factories directly.

        This is a backward-compatibility wrapper. New code should use:
            config = MySQLConnectorConfig.from_properties(properties)
            connector = MySQLConnector(config)

        Args:
            properties: Raw properties from runbook configuration

        Returns:
            Configured MySQLConnector instance

        Raises:
            ConnectorConfigError: If validation fails or required properties are missing

        """
        config = MySQLConnectorConfig.from_properties(properties)
        return cls(config)

    @contextmanager
    def _get_connection(self) -> Generator[Any, None, None]:
        """Get a database connection context manager.

        This method creates a new connection each time it's called to ensure
        thread safety and avoid connection state issues.

        Yields:
            MySQL connection object

        Raises:
            ConnectorExtractionError: If connection fails

        """
        connection = None
        try:
            connection = pymysql.connect(
                host=self._config.host,
                port=self._config.port,
                user=self._config.user,
                password=self._config.password,
                database=self._config.database,
                charset=self._config.charset,
                autocommit=self._config.autocommit,
                connect_timeout=self._config.connect_timeout,
            )

            yield connection

        except Exception as e:
            logger.error(f"Failed to connect to MySQL: {e}")
            raise ConnectorExtractionError(f"MySQL connection failed: {e}") from e
        finally:
            if connection:
                connection.close()

    def _execute_query(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> list[dict[str, Any]]:
        """Execute a SQL query and return results.

        Args:
            query: SQL query to execute
            params: Optional query parameters for parameterized queries

        Returns:
            List of dictionaries representing query results

        Raises:
            ConnectorExtractionError: If query execution fails

        """
        try:
            with self._get_connection() as connection:
                with connection.cursor() as cursor:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)

                    # Get column names
                    columns = (
                        [desc[0] for desc in cursor.description]
                        if cursor.description
                        else []
                    )

                    # Fetch all results
                    rows = cursor.fetchall()

                    # Convert to list of dictionaries
                    results: list[dict[str, Any]] = []
                    for row in rows:
                        row_dict = dict(zip(columns, row, strict=True))
                        results.append(row_dict)

                    return results

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise ConnectorExtractionError(f"Query execution failed: {e}") from e

    def _get_database_metadata(self) -> dict[str, Any]:
        """Extract database metadata including tables, columns, and constraints.

        Returns:
            Dictionary containing database metadata

        """
        try:
            metadata: dict[str, Any] = {
                "database_name": self._config.database,
                "tables": [],
                "server_info": {},
            }

            with self._get_connection() as connection:
                # Get server information
                # Type ignore: it is a pymysql issue.
                server_info = connection.get_server_info()  # type: ignore
                metadata["server_info"] = {
                    "version": server_info,
                    "host": self._config.host,
                    "port": self._config.port,
                }

                # Get table information
                tables: list[dict[str, Any]] = self._execute_query(
                    _TABLES_QUERY, (self._config.database,)
                )

                for table in tables:
                    table_info: dict[str, Any] = {
                        "name": table["TABLE_NAME"],
                        "type": table["TABLE_TYPE"],
                        "comment": table["TABLE_COMMENT"],
                        "estimated_rows": table["TABLE_ROWS"],
                        "columns": [],
                    }

                    # Get column information for each table
                    columns = self._execute_query(
                        _COLUMNS_QUERY, (self._config.database, table["TABLE_NAME"])
                    )
                    table_info["columns"] = columns

                    metadata["tables"].append(table_info)

                return metadata

        except Exception as e:
            logger.error(f"Failed to extract database metadata: {e}")
            raise ConnectorExtractionError(
                f"Database metadata extraction failed: {e}"
            ) from e

    def _get_table_data(
        self, table_name: str, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Get actual data from a specific table.

        Args:
            table_name: Name of the table to extract data from
            limit: Maximum number of rows to fetch per table (uses max_rows_per_table if None)

        Returns:
            List of dictionaries representing table rows

        """
        try:
            # Use configured limit if not specified
            effective_limit = (
                limit if limit is not None else self._config.max_rows_per_table
            )

            # Safe to use table name since it's verified to exist in information_schema
            # Using backticks to handle table names with special characters
            query = f"SELECT * FROM `{table_name}` LIMIT %s"  # noqa # nosec B608
            return self._execute_query(query, (effective_limit,))
        except Exception as e:
            logger.warning(f"Failed to extract data from table {table_name}: {e}")
            return []

    @override
    def extract(self, output_schema: Schema) -> Message:
        """Extract data from MySQL database.

        This method extracts database metadata and can execute custom queries
        if specified in the configuration.

        Args:
            output_schema: WCT schema for data validation

        Returns:
            Message containing extracted data in WCF schema format

        """
        try:
            logger.info(f"Extracting data from MySQL database: {self._config.database}")

            output_schema = DatabaseSchemaUtils.validate_output_schema(
                output_schema, _SUPPORTED_OUTPUT_SCHEMAS
            )

            # Extract database metadata (connection test included)
            metadata = self._get_database_metadata()

            # TODO: This should be strongly typed - even just a TypedDict
            # Transform data for standard_input schema
            extracted_data = self._transform_for_standard_input_schema(
                output_schema, metadata
            )

            # Create and validate message
            message = Message(
                id=f"MySQL data from {self._config.database}@{self._config.host}",
                content=extracted_data,
                schema=output_schema,
            )

            message.validate()

            return message

        except Exception as e:
            logger.error(f"MySQL extraction failed: {e}")
            raise ConnectorExtractionError(f"MySQL extraction failed: {e}") from e

    def _transform_for_standard_input_schema(
        self, schema: Schema, metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """Transform MySQL data for the 'standard_input' schema.

        This method extracts database content into granular text data items for compliance analysis:
        1. Each cell content as a separate data item
        2. Detailed metadata for complete traceability
        3. Database schema attached to top-level metadata

        Design Rationale:
        - Granular extraction enables precise personal data identification
        - Each data item can be traced back to exact database location
        - Supports compliance requirements for data mapping and audit trails
        - Cell content analysis is sufficient as empty tables have no personal data

        Args:
            schema: The standard_input schema
            metadata: Database metadata including table/column structure

        Returns:
            Standard_input schema compliant content with granular data items

        """
        data_items: list[dict[str, Any]] = []
        database_source = (
            f"{self._config.host}:{self._config.port}/{self._config.database}"
        )

        # Extract actual cell data from each table
        for table_info in metadata.get("tables", []):
            table_data_items = self._extract_table_cell_data(table_info)
            data_items.extend(table_data_items)

        return {
            "schemaVersion": schema.version,
            "name": f"mysql_text_from_{self._config.database}",
            "description": f"Text content extracted from MySQL database: {self._config.database}",
            "contentEncoding": "utf-8",
            "source": database_source,
            # Top-level metadata includes complete database schema for reference
            "metadata": {
                "connector_type": "mysql",  # Standard connector type field
                "connection_info": {
                    "host": self._config.host,
                    "port": self._config.port,
                    "database": self._config.database,
                    "user": self._config.user,
                },
                "database_schema": metadata,  # Complete database schema for traceability
                "total_data_items": len(data_items),
                "extraction_summary": {
                    "tables_processed": len(metadata.get("tables", [])),
                    "cell_values_extracted": len(data_items),
                    "max_rows_per_table": self._config.max_rows_per_table,
                },
            },
            "data": data_items,
        }

    def _extract_table_cell_data(
        self, table_info: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Extract cell data from a single table.

        Args:
            table_info: Table metadata including name and columns

        Returns:
            List of data items with cell content and metadata

        """
        data_items: list[dict[str, Any]] = []
        table_name = table_info["name"]

        # Extract actual cell data from the table (limited by max_rows_per_table)
        try:
            table_data = self._get_table_data(table_name)

            for row_index, row in enumerate(table_data):
                for column_name, cell_value in row.items():
                    # Only extract non-null, non-empty values
                    if DatabaseExtractionUtils.filter_non_empty_cell(cell_value):
                        # Create RelationalDatabaseMetadata for the cell
                        cell_metadata = RelationalDatabaseMetadata(
                            source=f"mysql_database_({self._config.database})_table_({table_name})_column_({column_name})_row_({row_index + 1})",
                            connector_type=_CONNECTOR_NAME,
                            table_name=table_name,
                            column_name=column_name,
                            schema_name=self._config.database,
                        )

                        # Use utility to create the data item
                        data_item = DatabaseExtractionUtils.create_cell_data_item(
                            cell_value, cell_metadata
                        )
                        data_items.append(data_item.model_dump())

        except Exception as e:
            logger.warning(f"Failed to extract data from table {table_name}: {e}")

        return data_items

    def _get_column_data_type(
        self, table_info: dict[str, Any], column_name: str
    ) -> str:
        """Get the SQL data type for a specific column.

        Args:
            table_info: Table metadata including columns
            column_name: Name of the column

        Returns:
            SQL data type or "unknown" if not found

        """
        return next(
            (
                col.get("DATA_TYPE")
                for col in table_info.get("columns", [])
                if col.get("COLUMN_NAME") == column_name
            ),
            "unknown",
        )
