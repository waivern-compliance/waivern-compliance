"""MySQL database connector for WCT compliance data extraction.

This module provides:
- MySQLConnector: Main connector class for MySQL database integration
- Support for extracting database metadata and content
- Transformation capabilities for standard_input schema
- Connection management with proper error handling and logging
"""

import logging
import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import pymysql
from typing_extensions import Self, override

from wct.connectors.base import (
    Connector,
    ConnectorConfigError,
    ConnectorExtractionError,
)
from wct.message import Message
from wct.schemas import Schema, StandardInputSchema

logger = logging.getLogger(__name__)

# Constants
_CONNECTOR_NAME = "mysql"
_DEFAULT_PORT = 3306
_DEFAULT_CHARSET = "utf8mb4"
_DEFAULT_AUTOCOMMIT = True
_DEFAULT_CONNECT_TIMEOUT = 10
_DEFAULT_MAX_ROWS = 10
_DEFAULT_SCHEMA_VERSION = "1.0.0"

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

_SUPPORTED_OUTPUT_SCHEMAS: list[Schema] = [
    StandardInputSchema(),
]


class MySQLConnector(Connector):
    """MySQL database connector for extracting data and metadata.

    This connector connects to a MySQL database and can execute queries
    to extract data and transform it into supported Schema formats
    for compliance analysis.
    """

    def __init__(
        self,
        host: str,
        port: int = _DEFAULT_PORT,
        user: str = "",
        password: str | None = None,
        database: str = "",
        charset: str = _DEFAULT_CHARSET,
        autocommit: bool = _DEFAULT_AUTOCOMMIT,
        connect_timeout: int = _DEFAULT_CONNECT_TIMEOUT,
        max_rows_per_table: int = _DEFAULT_MAX_ROWS,
    ) -> None:
        """Initialise MySQL connector with connection parameters.

        Args:
            host: MySQL server hostname or IP address
            port: MySQL server port (default: 3306)
            user: Database username
            password: Database password
            database: Database name to connect to
            charset: Character set for the connection (default: utf8mb4)
            autocommit: Enable autocommit mode (default: True)
            connect_timeout: Connection timeout in seconds (default: 10)
            max_rows_per_table: Maximum number of rows to extract per table (default: 10)

        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password or ""
        self.database = database
        self.charset = charset
        self.autocommit = autocommit
        self.connect_timeout = connect_timeout
        self.max_rows_per_table = max_rows_per_table

        self._validate_required_connection_parameters(host, user)

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
        """Create connector from configuration properties.

        Required properties:
        - host: MySQL server hostname (or MYSQL_HOST env var)
        - user: Database username (or MYSQL_USER env var)

        Optional properties:
        - port: Server port (default: 3306, or MYSQL_PORT env var)
        - password: Database password (or MYSQL_PASSWORD env var)
        - database: Database name (or MYSQL_DATABASE env var)
        - charset: Character set (default: "utf8mb4")
        - autocommit: Enable autocommit (default: True)
        - connect_timeout: Connection timeout (default: 10)
        - max_rows_per_table: Maximum rows per table (default: 10)
        """
        # Load environment variables, with runbook properties as fallback
        host, user = cls._validate_required_properties(properties)
        password = os.getenv("MYSQL_PASSWORD") or properties.get("password")
        database = os.getenv("MYSQL_DATABASE") or properties.get("database", "")
        port = cls._parse_port_from_env_or_properties(properties)

        return cls(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset=properties.get("charset", _DEFAULT_CHARSET),
            autocommit=properties.get("autocommit", _DEFAULT_AUTOCOMMIT),
            connect_timeout=properties.get("connect_timeout", _DEFAULT_CONNECT_TIMEOUT),
            max_rows_per_table=properties.get("max_rows_per_table", _DEFAULT_MAX_ROWS),
        )

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
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset=self.charset,
                autocommit=self.autocommit,
                connect_timeout=self.connect_timeout,
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
                "database_name": self.database,
                "tables": [],
                "server_info": {},
            }

            with self._get_connection() as connection:
                # Get server information
                # Type ignore: it is a pymysql issue.
                server_info = connection.get_server_info()  # type: ignore
                metadata["server_info"] = {
                    "version": server_info,
                    "host": self.host,
                    "port": self.port,
                }

                # Get table information
                tables: list[dict[str, Any]] = self._execute_query(
                    _TABLES_QUERY, (self.database,)
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
                        _COLUMNS_QUERY, (self.database, table["TABLE_NAME"])
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
            effective_limit = limit if limit is not None else self.max_rows_per_table

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
            logger.info(f"Extracting data from MySQL database: {self.database}")

            output_schema = self._validate_output_schema(output_schema)

            # Extract database metadata (connection test included)
            metadata = self._get_database_metadata()

            # Transform data for standard_input schema
            extracted_data = self._transform_for_standard_input_schema(
                output_schema, metadata
            )

            # Create and validate message
            message = Message(
                id=f"MySQL data from {self.database}@{self.host}",
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
        database_source = f"{self.host}:{self.port}/{self.database}"

        # Extract actual cell data from each table
        for table_info in metadata.get("tables", []):
            table_data_items = self._extract_table_cell_data(table_info)
            data_items.extend(table_data_items)

        return {
            "schemaVersion": _DEFAULT_SCHEMA_VERSION,
            "name": f"mysql_text_from_{self.database}",
            "description": f"Text content extracted from MySQL database: {self.database}",
            "contentEncoding": "utf-8",
            "source": database_source,
            # Top-level metadata includes complete database schema for reference
            "metadata": {
                "extraction_type": "mysql_to_text",
                "connection_info": {
                    "host": self.host,
                    "port": self.port,
                    "database": self.database,
                    "user": self.user,
                },
                "database_schema": metadata,  # Complete database schema for traceability
                "total_data_items": len(data_items),
                "extraction_summary": {
                    "tables_processed": len(metadata.get("tables", [])),
                    "cell_values_extracted": len(data_items),
                    "max_rows_per_table": self.max_rows_per_table,
                },
            },
            "data": data_items,
        }

    @classmethod
    def _validate_required_properties(
        cls, properties: dict[str, Any]
    ) -> tuple[str, str]:
        """Validate and extract required properties from configuration.

        Args:
            properties: Configuration properties dictionary

        Returns:
            Tuple of (host, user)

        Raises:
            ConnectorConfigError: If required properties are missing

        """
        host = os.getenv("MYSQL_HOST") or properties.get("host")
        user = os.getenv("MYSQL_USER") or properties.get("user")

        # Use specific error messages for configuration context
        if not host:
            raise ConnectorConfigError(
                "MySQL host info is required (specify in runbook or MYSQL_HOST env var)"
            )
        if not user:
            raise ConnectorConfigError(
                "MySQL user info is required (specify in runbook or MYSQL_USER env var)"
            )

        return host, user

    def _validate_required_connection_parameters(self, host: str, user: str) -> None:
        """Validate required connection parameters.

        Args:
            host: MySQL server hostname
            user: Database username

        Raises:
            ConnectorConfigError: If required parameters are missing

        """
        if not host:
            raise ConnectorConfigError("MySQL host is required")
        if not user:
            raise ConnectorConfigError("MySQL user is required")

    @classmethod
    def _parse_port_from_env_or_properties(cls, properties: dict[str, Any]) -> int:
        """Parse port from environment variable or properties.

        Args:
            properties: Configuration properties dictionary

        Returns:
            Port number

        Raises:
            ConnectorConfigError: If port value is invalid

        """
        port_str = os.getenv("MYSQL_PORT")
        if port_str:
            try:
                return int(port_str)
            except ValueError as e:
                raise ConnectorConfigError(
                    f"Invalid MYSQL_PORT environment variable: {port_str}"
                ) from e
        return properties.get("port", _DEFAULT_PORT)

    def _validate_output_schema(self, output_schema: Schema | None) -> Schema:
        """Validate the output schema.

        Args:
            output_schema: Schema to validate

        Returns:
            The validated schema (or default if none provided)

        Raises:
            ConnectorConfigError: If schema is invalid or unsupported

        """
        if not output_schema:
            logger.warning("No schema provided, using default schema")
            output_schema = _SUPPORTED_OUTPUT_SCHEMAS[0]

        supported_schema_names = [schema.name for schema in _SUPPORTED_OUTPUT_SCHEMAS]
        if output_schema.name not in supported_schema_names:
            raise ConnectorConfigError(
                f"Unsupported output schema: {output_schema.name}. "
                f"Supported schemas: {supported_schema_names}"
            )

        return output_schema

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
                    if cell_value is not None and str(cell_value).strip():
                        data_items.append(
                            self._create_cell_data_item(
                                table_info,
                                table_name,
                                column_name,
                                cell_value,
                                row_index,
                            )
                        )

        except Exception as e:
            logger.warning(f"Failed to extract data from table {table_name}: {e}")

        return data_items

    def _create_cell_data_item(
        self,
        table_info: dict[str, Any],
        table_name: str,
        column_name: str,
        cell_value: Any,  # noqa: ANN401  # Database cell values can be any type (str, int, float, date, None, etc.)
        row_index: int,
    ) -> dict[str, Any]:
        """Create a single cell data item with metadata.

        Args:
            table_info: Table metadata
            table_name: Name of the table
            column_name: Name of the column
            cell_value: The cell value
            row_index: Zero-based row index

        Returns:
            Data item dictionary with content and metadata

        """
        return {
            "content": str(cell_value),
            "metadata": {
                "source": f"mysql_cell_data_table_({table_name})_column_({column_name})",
                "description": f"Cell data from `{table_name}.{column_name}` row {row_index + 1}",
                "data_type": "cell_content",
                "database": self.database,
                "table": table_name,
                "column": column_name,
                "row_index": row_index + 1,
                "host": self.host,
                "port": self.port,
                # Include column metadata for context
                "sql_data_type": self._get_column_data_type(table_info, column_name),
            },
        }

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
