"""MySQL database connector for WCT compliance data extraction.

This module provides:
- MySQLConnector: Main connector class for MySQL database integration
- Support for extracting database metadata and content
- Transformation capabilities for standard_input schema
- Connection management with proper error handling and logging
"""

import importlib
import logging
from collections.abc import Generator
from contextlib import contextmanager
from types import ModuleType
from typing import Any, override

import pymysql
from waivern_connectors_database import (
    ColumnMetadata,
    DatabaseExtractionUtils,
    RelationalExtractionMetadata,
    RelationalProducerConfig,
    ServerInfo,
    TableMetadata,
)
from waivern_core import validate_output_schema
from waivern_core.base_connector import Connector
from waivern_core.errors import (
    ConnectorConfigError,
    ConnectorExtractionError,
)
from waivern_core.message import Message
from waivern_core.schemas import (
    RelationalDatabaseMetadata,
    Schema,
    StandardInputDataItemModel,
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

_SUPPORTED_OUTPUT_SCHEMAS: list[Schema] = [Schema("standard_input", "1.0.0")]


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

    def _load_producer(self, schema: Schema) -> ModuleType:
        """Dynamically import producer module.

        Python's import system automatically caches modules in sys.modules,
        so repeated imports are fast and don't require manual caching.

        Args:
            schema: The schema to load producer for

        Returns:
            Producer module with produce() function

        Raises:
            ModuleNotFoundError: If producer module doesn't exist for this version

        """
        module_name = f"{schema.name}_{schema.version.replace('.', '_')}"
        return importlib.import_module(f"waivern_mysql.schema_producers.{module_name}")

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Return the output schemas supported by this connector."""
        return _SUPPORTED_OUTPUT_SCHEMAS

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

    def _get_database_metadata(self) -> RelationalExtractionMetadata:
        """Extract database metadata including tables, columns, and constraints.

        Returns:
            Typed extraction metadata with tables and server info

        """
        try:
            tables_metadata: list[TableMetadata] = []

            with self._get_connection() as connection:
                # Get server information
                # Type ignore: it is a pymysql issue.
                server_version = connection.get_server_info()  # type: ignore
                server_info = ServerInfo(
                    version=server_version,
                    host=self._config.host,
                    port=self._config.port,
                )

                # Get table information
                tables_raw: list[dict[str, Any]] = self._execute_query(
                    _TABLES_QUERY, (self._config.database,)
                )

                for table in tables_raw:
                    # Get column information for each table
                    columns_raw = self._execute_query(
                        _COLUMNS_QUERY, (self._config.database, table["TABLE_NAME"])
                    )

                    columns_metadata = [
                        ColumnMetadata(
                            name=col["COLUMN_NAME"],
                            data_type=col["DATA_TYPE"],
                            is_nullable=col["IS_NULLABLE"] == "YES",
                            default=col["COLUMN_DEFAULT"],
                            comment=col["COLUMN_COMMENT"] or None,
                            key=col["COLUMN_KEY"] or None,
                            extra=col["EXTRA"] or None,
                        )
                        for col in columns_raw
                    ]

                    table_metadata = TableMetadata(
                        name=table["TABLE_NAME"],
                        table_type=table["TABLE_TYPE"],
                        comment=table["TABLE_COMMENT"] or None,
                        estimated_rows=table["TABLE_ROWS"],
                        columns=columns_metadata,
                    )
                    tables_metadata.append(table_metadata)

                return RelationalExtractionMetadata(
                    database_name=self._config.database,
                    tables=tables_metadata,
                    server_info=server_info,
                )

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

            validate_output_schema(output_schema, _SUPPORTED_OUTPUT_SCHEMAS)

            # Extract database metadata (connection test included)
            metadata = self._get_database_metadata()

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

            return message

        except (ConnectorConfigError, ConnectorExtractionError):
            # Re-raise connector errors as-is (don't wrap config errors)
            raise
        except Exception as e:
            logger.error(f"MySQL extraction failed: {e}")
            raise ConnectorExtractionError(f"MySQL extraction failed: {e}") from e

    def _transform_for_standard_input_schema(
        self, schema: Schema, metadata: RelationalExtractionMetadata
    ) -> dict[str, Any]:
        """Transform MySQL data for the 'standard_input' schema using producer module.

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
            metadata: Typed extraction metadata with tables and server info

        Returns:
            Standard_input schema compliant content with granular data items

        """
        data_items: list[StandardInputDataItemModel[RelationalDatabaseMetadata]] = []

        # Extract actual cell data from each table
        for table in metadata.tables:
            table_data_items = self._extract_table_cell_data(table)
            data_items.extend(table_data_items)

        # Load the appropriate producer for this schema version
        producer = self._load_producer(schema)

        # Prepare typed config for producer
        config_data = RelationalProducerConfig(
            database=self._config.database,
            max_rows_per_table=self._config.max_rows_per_table,
            host=self._config.host,
            port=self._config.port,
            user=self._config.user,
        )

        # Delegate transformation to producer
        return producer.produce(
            schema_version=schema.version,
            metadata=metadata,
            data_items=data_items,
            config_data=config_data,
        )

    def _extract_table_cell_data(
        self, table: TableMetadata
    ) -> list[StandardInputDataItemModel[RelationalDatabaseMetadata]]:
        """Extract cell data from a single table.

        Args:
            table: Typed table metadata including name and columns

        Returns:
            List of typed data items with cell content and metadata

        """
        data_items: list[StandardInputDataItemModel[RelationalDatabaseMetadata]] = []

        # Extract actual cell data from the table (limited by max_rows_per_table)
        try:
            table_data = self._get_table_data(table.name)

            for row_index, row in enumerate(table_data):
                for column_name, cell_value in row.items():
                    # Only extract non-null, non-empty values
                    if DatabaseExtractionUtils.filter_non_empty_cell(cell_value):
                        # Create RelationalDatabaseMetadata for the cell
                        cell_metadata = RelationalDatabaseMetadata(
                            source=f"mysql_database_({self._config.database})_table_({table.name})_column_({column_name})_row_({row_index + 1})",
                            connector_type=_CONNECTOR_NAME,
                            table_name=table.name,
                            column_name=column_name,
                            schema_name=self._config.database,
                        )

                        # Use utility to create the data item (returns typed model)
                        data_item = DatabaseExtractionUtils.create_cell_data_item(
                            cell_value, cell_metadata
                        )
                        data_items.append(data_item)

        except Exception as e:
            logger.warning(f"Failed to extract data from table {table.name}: {e}")

        return data_items
