"""SQLite database connector for WCT compliance data extraction."""

import importlib
import logging
import sqlite3
from pathlib import Path
from types import ModuleType
from typing import Any, override

from waivern_connectors_database import (
    ColumnMetadata,
    DatabaseConnector,
    DatabaseExtractionUtils,
    RelationalExtractionMetadata,
    RelationalProducerConfig,
    TableMetadata,
)
from waivern_core import validate_output_schema
from waivern_core.errors import ConnectorConfigError, ConnectorExtractionError
from waivern_core.message import Message
from waivern_core.schemas import (
    RelationalDatabaseMetadata,
    Schema,
    StandardInputDataItemModel,
)

from waivern_sqlite.config import SQLiteConnectorConfig

logger = logging.getLogger(__name__)

# Constants
_SUPPORTED_OUTPUT_SCHEMAS: list[Schema] = [Schema("standard_input", "1.0.0")]


class SQLiteConnector(DatabaseConnector):
    """SQLite database connector for extracting data and metadata.

    This connector connects to a SQLite database file and can execute queries
    to extract data and transform it into supported Schema formats
    for compliance analysis.
    """

    def __init__(self, config: SQLiteConnectorConfig) -> None:
        """Initialise SQLite connector with validated configuration.

        Args:
            config: Validated SQLite connector configuration

        """
        self._config = config

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the connector."""
        return "sqlite_connector"

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
        return importlib.import_module(f"waivern_sqlite.schema_producers.{module_name}")

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Return the output schemas supported by this connector."""
        return _SUPPORTED_OUTPUT_SCHEMAS

    @override
    def extract(self, output_schema: Schema) -> Message:
        """Extract data from SQLite database.

        This method extracts database metadata and can execute custom queries
        if specified in the configuration.

        Args:
            output_schema: WCT schema for data validation

        Returns:
            Message containing extracted data in WCF schema format

        """
        try:
            logger.info(
                f"Extracting data from SQLite database: {self._config.database_path}"
            )

            validate_output_schema(output_schema, _SUPPORTED_OUTPUT_SCHEMAS)

            # Extract database metadata (connection test included)
            metadata = self._get_database_metadata()

            # Transform data for standard_input schema
            extracted_data = self._transform_for_standard_input_schema(
                output_schema, metadata
            )

            # Create and validate message
            message = Message(
                id=f"SQLite data from {Path(self._config.database_path).stem}",
                content=extracted_data,
                schema=output_schema,
            )

            return message

        except (ConnectorConfigError, ConnectorExtractionError):
            # Re-raise connector errors as-is (don't wrap config errors)
            raise
        except Exception as e:
            logger.error(f"SQLite extraction failed: {e}")
            raise ConnectorExtractionError(f"SQLite extraction failed: {e}") from e

    def _get_database_metadata(self) -> RelationalExtractionMetadata:
        """Extract database metadata including tables, columns, and constraints.

        Returns:
            Typed extraction metadata with tables (server_info is None for SQLite)

        """
        try:
            # Check if database file exists
            db_path = Path(self._config.database_path)
            if not db_path.exists():
                raise ConnectorExtractionError(
                    f"SQLite database file not found: {self._config.database_path}"
                )

            tables_metadata: list[TableMetadata] = []

            conn = sqlite3.connect(self._config.database_path)
            try:
                cursor = conn.cursor()

                # Get table information
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                table_names = cursor.fetchall()

                for (table_name,) in table_names:
                    # Skip tables with unsafe names for security
                    if not table_name.replace("_", "").replace("-", "").isalnum():
                        continue

                    # Get column information for each table
                    cursor.execute(f"PRAGMA table_info(`{table_name}`)")
                    pragma_results = cursor.fetchall()

                    columns_metadata = [
                        ColumnMetadata(
                            name=col_info[1],
                            data_type=col_info[2] or "TEXT",
                            is_nullable=not col_info[3],
                            default=col_info[4],
                            comment=None,
                            key="PRI" if col_info[5] else None,
                            extra=None,
                        )
                        for col_info in pragma_results
                    ]

                    # Get estimated row count
                    estimated_rows = 0
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")  # noqa: S608
                        estimated_rows = cursor.fetchone()[0]
                    except sqlite3.Error:
                        pass

                    table_metadata = TableMetadata(
                        name=table_name,
                        table_type="BASE TABLE",
                        comment=None,
                        estimated_rows=estimated_rows,
                        columns=columns_metadata,
                    )
                    tables_metadata.append(table_metadata)

                # SQLite is embedded, so server_info is None
                return RelationalExtractionMetadata(
                    database_name=db_path.stem,
                    tables=tables_metadata,
                    server_info=None,
                )

            finally:
                conn.close()

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

            conn = sqlite3.connect(self._config.database_path)
            try:
                cursor = conn.cursor()

                # Safe to use table name since it's verified to exist in sqlite_master
                # Using backticks to handle table names with special characters
                cursor.execute(
                    f"SELECT * FROM `{table_name}` LIMIT ?",  # noqa: S608
                    (effective_limit,),
                )
                rows = cursor.fetchall()

                # Get column names
                cursor.execute(f"PRAGMA table_info(`{table_name}`)")
                columns = [col[1] for col in cursor.fetchall()]

                # Convert to list of dictionaries
                results: list[dict[str, Any]] = []
                for row in rows:
                    row_dict = dict(zip(columns, row, strict=True))
                    results.append(row_dict)

                return results

            finally:
                conn.close()

        except Exception as e:
            logger.warning(f"Failed to extract data from table {table_name}: {e}")
            return []

    def _transform_for_standard_input_schema(
        self, schema: Schema, metadata: RelationalExtractionMetadata
    ) -> dict[str, Any]:
        """Transform SQLite data for the 'standard_input' schema using producer module.

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
            metadata: Typed extraction metadata with tables

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

        # Prepare typed config for producer (SQLite uses database name from path)
        config_data = RelationalProducerConfig(
            database=Path(self._config.database_path).stem,
            max_rows_per_table=self._config.max_rows_per_table,
            host=None,
            port=None,
            user=None,
        )

        # Delegate transformation to producer
        return producer.produce(
            schema_version=schema.version,
            metadata=metadata,
            data_items=data_items,
            config_data=config_data,
            database_path=self._config.database_path,
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
        db_name = Path(self._config.database_path).stem

        # Extract actual cell data from the table (limited by max_rows_per_table)
        try:
            table_data = self._get_table_data(table.name)

            for row_index, row in enumerate(table_data):
                for column_name, cell_value in row.items():
                    # Only extract non-null, non-empty values
                    if DatabaseExtractionUtils.filter_non_empty_cell(cell_value):
                        # Create RelationalDatabaseMetadata for the cell
                        cell_metadata = RelationalDatabaseMetadata(
                            source=f"sqlite_database_({db_name})_table_({table.name})_column_({column_name})_row_({row_index + 1})",
                            connector_type="sqlite_connector",
                            table_name=table.name,
                            column_name=column_name,
                            schema_name=db_name,
                        )

                        # Use utility to create the data item (returns typed model)
                        data_item = DatabaseExtractionUtils.create_cell_data_item(
                            cell_value, cell_metadata
                        )
                        data_items.append(data_item)

        except Exception as e:
            logger.warning(f"Failed to extract data from table {table.name}: {e}")

        return data_items
