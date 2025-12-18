"""Producer for standard_input schema version 1.0.0."""

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
) -> dict[str, Any]:
    """Transform MySQL data to standard_input v1.0.0 schema format.

    Uses Pydantic models to validate the output structure at producer time,
    ensuring schema compliance before returning.

    Args:
        schema_version: The schema version ("1.0.0")
        metadata: Typed extraction metadata including tables and server info
        data_items: List of validated data items with content and metadata
        config_data: Typed producer configuration

    Returns:
        Dictionary conforming to standard_input v1.0.0 schema structure

    """
    database_source = f"{config_data.host}:{config_data.port}/{config_data.database}"

    model = StandardInputDataModel[RelationalDatabaseMetadata](
        schemaVersion=schema_version,
        name=f"mysql_text_from_{config_data.database}",
        description=f"Text content extracted from MySQL database: {config_data.database}",
        contentEncoding="utf-8",
        source=database_source,
        metadata={
            "connector_type": "mysql",
            "connection_info": {
                "host": config_data.host,
                "port": config_data.port,
                "database": config_data.database,
                "user": config_data.user,
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
