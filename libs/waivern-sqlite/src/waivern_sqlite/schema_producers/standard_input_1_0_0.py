"""Producer for standard_input schema version 1.0.0."""

from pathlib import Path
from typing import Any

from waivern_connectors_database import (
    RelationalExtractionMetadata,
    RelationalProducerConfig,
)
from waivern_core.schemas import (
    RelationalDatabaseMetadata,
    StandardInputDataItemModel,
    StandardInputDataModel,
)


def produce(
    schema_version: str,
    metadata: RelationalExtractionMetadata,
    data_items: list[StandardInputDataItemModel[RelationalDatabaseMetadata]],
    config_data: RelationalProducerConfig,
    database_path: str,
) -> dict[str, Any]:
    """Transform SQLite data to standard_input v1.0.0 schema format.

    Uses Pydantic models to validate the output structure at producer time,
    ensuring schema compliance before returning.

    Args:
        schema_version: The schema version ("1.0.0")
        metadata: Typed extraction metadata including tables
        data_items: List of validated data items with content and metadata
        config_data: Typed producer configuration
        database_path: Path to the SQLite database file

    Returns:
        Dictionary conforming to standard_input v1.0.0 schema structure

    """
    database_source = str(Path(database_path).absolute())

    model = StandardInputDataModel[RelationalDatabaseMetadata](
        schemaVersion=schema_version,
        name=f"sqlite_text_from_{config_data.database}",
        description=f"Text content extracted from SQLite database: {database_path}",
        contentEncoding="utf-8",
        source=database_source,
        metadata={
            "connector_type": "sqlite_connector",
            "connection_info": {
                "database_path": database_path,
            },
            "database_schema": metadata.model_dump(),
            "total_data_items": len(data_items),
            "extraction_summary": {
                "tables_processed": len(metadata.tables),
                "cell_values_extracted": len(data_items),
                "max_rows_per_table": config_data.max_rows_per_table,
            },
        },
        data=data_items,
    )

    return model.model_dump()
