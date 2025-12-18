"""Producer for standard_input schema version 1.0.0."""

from typing import Any

from waivern_core.schemas import (
    DocumentDatabaseMetadata,
    StandardInputDataItemModel,
    StandardInputDataModel,
)

from waivern_mongodb.connector import ExtractionMetadata, ProducerConfig


def produce(
    schema_version: str,
    metadata: ExtractionMetadata,
    data_items: list[StandardInputDataItemModel[DocumentDatabaseMetadata]],
    config_data: ProducerConfig,
) -> dict[str, Any]:
    """Transform MongoDB data to standard_input v1.0.0 schema format.

    Uses Pydantic models to validate the output structure at producer time,
    ensuring schema compliance before returning.

    Args:
        schema_version: The schema version ("1.0.0")
        metadata: Typed extraction metadata including collections information
        data_items: List of validated data items with content and metadata
        config_data: Typed producer configuration

    Returns:
        Dictionary conforming to standard_input v1.0.0 schema structure

    """
    model = StandardInputDataModel[DocumentDatabaseMetadata](
        schemaVersion=schema_version,
        name=f"mongodb_text_from_{config_data.database}",
        description=f"Text content extracted from MongoDB database: {config_data.database}",
        contentEncoding="utf-8",
        source=f"{config_data.uri}/{config_data.database}",
        metadata={
            "connector_type": "mongodb",
            "connection_info": {
                "uri": config_data.uri,
                "database": config_data.database,
            },
            "collections": [c.model_dump() for c in metadata.collections],
            "total_data_items": len(data_items),
            "extraction_summary": {
                "collections_processed": len(metadata.collections),
                "field_values_extracted": len(data_items),
                "sample_size_per_collection": config_data.sample_size,
            },
        },
        data=data_items,
    )

    return model.model_dump()
