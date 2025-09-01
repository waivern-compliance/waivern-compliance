"""SQLite database connector for WCT compliance data extraction."""

import logging
import sqlite3
from pathlib import Path
from typing import Any, Self, override

from wct.connectors.base import ConnectorConfigError, ConnectorExtractionError
from wct.connectors.database.base_connector import DatabaseConnector
from wct.connectors.sqlite.config import SQLiteConnectorConfig
from wct.message import Message
from wct.schemas import RelationalDatabaseMetadata, Schema, StandardInputSchema

logger = logging.getLogger(__name__)

# Constants
_SUPPORTED_OUTPUT_SCHEMAS: list[Schema] = [
    StandardInputSchema(),
]


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
        return "sqlite"

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Return the output schemas supported by this connector."""
        return _SUPPORTED_OUTPUT_SCHEMAS

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create connector from configuration properties.

        Args:
            properties: Raw properties from runbook configuration

        Returns:
            Configured SQLite connector instance

        """
        config = SQLiteConnectorConfig.from_properties(properties)
        return cls(config)

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

            output_schema = self._validate_output_schema(output_schema)

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

            message.validate()

            return message

        except Exception as e:
            logger.error(f"SQLite extraction failed: {e}")
            raise ConnectorExtractionError(f"SQLite extraction failed: {e}") from e

    def _get_database_metadata(self) -> dict[str, Any]:
        """Extract database metadata including tables, columns, and constraints.

        Returns:
            Dictionary containing database metadata

        """
        try:
            # Check if database file exists
            db_path = Path(self._config.database_path)
            if not db_path.exists():
                raise ConnectorExtractionError(
                    f"SQLite database file not found: {self._config.database_path}"
                )

            metadata: dict[str, Any] = {
                "database_name": db_path.stem,
                "tables": [],
                "server_info": {},
            }

            conn = sqlite3.connect(self._config.database_path)
            try:
                # Get server information (SQLite version)
                cursor = conn.cursor()
                cursor.execute("SELECT sqlite_version()")
                sqlite_version = cursor.fetchone()[0]
                metadata["server_info"] = {
                    "version": f"SQLite {sqlite_version}",
                    "database_path": self._config.database_path,
                }

                # Get table information
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                table_names = cursor.fetchall()

                for (table_name,) in table_names:
                    # Skip tables with unsafe names for security
                    if not table_name.replace("_", "").replace("-", "").isalnum():
                        continue

                    table_info: dict[str, Any] = {
                        "name": table_name,
                        "type": "BASE TABLE",
                        "comment": "",
                        "estimated_rows": 0,
                        "columns": [],
                    }

                    # Get column information for each table
                    cursor.execute(f"PRAGMA table_info(`{table_name}`)")
                    pragma_results = cursor.fetchall()

                    for col_info in pragma_results:
                        # pragma_results format: (cid, name, type, notnull, dflt_value, pk)
                        column_info = {
                            "COLUMN_NAME": col_info[1],
                            "DATA_TYPE": col_info[2],
                            "IS_NULLABLE": "NO" if col_info[3] else "YES",
                            "COLUMN_DEFAULT": col_info[4],
                            "COLUMN_COMMENT": "",
                            "COLUMN_KEY": "PRI" if col_info[5] else "",
                            "EXTRA": "",
                        }
                        table_info["columns"].append(column_info)

                    # Get estimated row count
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")  # noqa: S608
                        row_count = cursor.fetchone()[0]
                        table_info["estimated_rows"] = row_count
                    except sqlite3.Error:
                        # If count fails, keep default 0
                        pass

                    metadata["tables"].append(table_info)

                return metadata

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
        self, schema: Schema, metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """Transform SQLite data for the 'standard_input' schema.

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
        database_source = str(Path(self._config.database_path).absolute())

        # Extract actual cell data from each table
        for table_info in metadata.get("tables", []):
            table_data_items = self._extract_table_cell_data(table_info)
            data_items.extend(table_data_items)

        return {
            "schemaVersion": schema.version,
            "name": f"sqlite_text_from_{Path(self._config.database_path).stem}",
            "description": f"Text content extracted from SQLite database: {self._config.database_path}",
            "contentEncoding": "utf-8",
            "source": database_source,
            # Top-level metadata includes complete database schema for reference
            "metadata": {
                "connector_type": "sqlite",  # Standard connector type field
                "connection_info": {
                    "database_path": self._config.database_path,
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
        # Create RelationalDatabaseMetadata instance
        metadata = RelationalDatabaseMetadata(
            source=f"sqlite_database_({Path(self._config.database_path).stem})_table_({table_name})_column_({column_name})_row_({row_index + 1})",
            connector_type="sqlite",
            table_name=table_name,
            column_name=column_name,
            schema_name=Path(
                self._config.database_path
            ).stem,  # Use filename as schema name for SQLite
        )

        return {
            "content": str(cell_value),
            "metadata": metadata.model_dump(),
        }
