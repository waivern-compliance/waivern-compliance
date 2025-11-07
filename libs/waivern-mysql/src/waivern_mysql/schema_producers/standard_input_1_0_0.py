"""Producer for standard_input schema version 1.0.0."""

from typing import Any


def produce(
    schema_version: str,
    metadata: dict[str, Any],
    data_items: list[dict[str, Any]],
    config_data: dict[str, Any],
) -> dict[str, Any]:
    """Transform MySQL data to standard_input v1.0.0 schema format.

    Args:
        schema_version: The schema version ("1.0.0")
        metadata: Database metadata including tables, columns, and constraints
        data_items: List of extracted cell data items with content and metadata
        config_data: Configuration data with 'host', 'port', 'database', 'user', 'max_rows_per_table' keys

    Returns:
        Dictionary conforming to standard_input v1.0.0 schema structure

    """
    # Extract config values
    host: str = config_data["host"]
    port: int = config_data["port"]
    database: str = config_data["database"]
    user: str = config_data["user"]
    max_rows_per_table: int = config_data["max_rows_per_table"]

    database_source = f"{host}:{port}/{database}"

    return {
        "schemaVersion": schema_version,
        "name": f"mysql_text_from_{database}",
        "description": f"Text content extracted from MySQL database: {database}",
        "contentEncoding": "utf-8",
        "source": database_source,
        # Top-level metadata includes complete database schema for reference
        "metadata": {
            "connector_type": "mysql",  # Standard connector type field
            "connection_info": {
                "host": host,
                "port": port,
                "database": database,
                "user": user,
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
