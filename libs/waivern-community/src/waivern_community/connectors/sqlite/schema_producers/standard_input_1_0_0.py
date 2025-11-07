"""Producer for standard_input schema version 1.0.0."""

from pathlib import Path
from typing import Any


def produce(
    schema_version: str,
    metadata: dict[str, Any],
    data_items: list[dict[str, Any]],
    config_data: dict[str, Any],
) -> dict[str, Any]:
    """Transform SQLite data to standard_input v1.0.0 schema format.

    Args:
        schema_version: The schema version ("1.0.0")
        metadata: Database metadata including tables, columns, and constraints
        data_items: List of extracted cell data items with content and metadata
        config_data: Configuration data with 'database_path', 'max_rows_per_table' keys

    Returns:
        Dictionary conforming to standard_input v1.0.0 schema structure

    """
    # Extract config values
    database_path: str = config_data["database_path"]
    max_rows_per_table: int = config_data["max_rows_per_table"]

    database_source = str(Path(database_path).absolute())

    return {
        "schemaVersion": schema_version,
        "name": f"sqlite_text_from_{Path(database_path).stem}",
        "description": f"Text content extracted from SQLite database: {database_path}",
        "contentEncoding": "utf-8",
        "source": database_source,
        # Top-level metadata includes complete database schema for reference
        "metadata": {
            "connector_type": "sqlite_connector",  # Standard connector type field
            "connection_info": {
                "database_path": database_path,
            },
            "database_schema": metadata,  # Complete database schema for traceability
            "total_data_items": len(data_items),
            "extraction_summary": {
                "tables_processed": len(metadata.get("tables", [])),
                "cell_values_extracted": len(data_items),
                "max_rows_per_table": max_rows_per_table,
            },
        },
        "data": data_items,
    }
