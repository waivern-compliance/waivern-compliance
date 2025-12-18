"""MongoDB connector for extracting data from MongoDB databases."""

import importlib
import logging
from types import ModuleType
from typing import Any, cast, override

from bson import ObjectId
from pydantic import BaseModel, Field
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from waivern_core import Schema
from waivern_core.base_connector import Connector
from waivern_core.errors import ConnectorExtractionError
from waivern_core.message import Message
from waivern_core.schemas import (
    DocumentDatabaseMetadata,
    StandardInputDataItemModel,
)

from waivern_mongodb.config import MongoDBConnectorConfig

# Type alias for MongoDB documents (schemaless by design)
MongoDocument = dict[str, Any]


class CollectionMetadata(BaseModel):
    """Metadata for a single MongoDB collection."""

    name: str = Field(description="Name of the collection")
    document_count: int = Field(description="Estimated document count")


class ExtractionMetadata(BaseModel):
    """Metadata passed to the schema producer."""

    collections: list[CollectionMetadata] = Field(
        description="List of collection metadata"
    )


class ProducerConfig(BaseModel):
    """Configuration passed to the schema producer."""

    uri: str = Field(description="MongoDB connection URI")
    database: str = Field(description="Database name")
    sample_size: int = Field(description="Sample size per collection")


logger = logging.getLogger(__name__)

_CONNECTOR_NAME = "mongodb"
_SUPPORTED_OUTPUT_SCHEMAS: list[Schema] = [Schema("standard_input", "1.0.0")]


class MongoDBConnector(Connector):
    """MongoDB connector for extracting data and metadata.

    This connector connects to a MongoDB database and extracts document data,
    transforming it into the standard_input schema format for compliance analysis.
    """

    def __init__(self, config: MongoDBConnectorConfig) -> None:
        """Initialise MongoDB connector with validated configuration.

        Args:
            config: Validated MongoDB connector configuration

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

    def _load_producer(self, schema: Schema) -> ModuleType:
        """Dynamically import producer module for the given schema.

        Args:
            schema: The schema to load producer for

        Returns:
            Producer module with produce() function

        """
        module_name = f"{schema.name}_{schema.version.replace('.', '_')}"
        return importlib.import_module(
            f"waivern_mongodb.schema_producers.{module_name}"
        )

    @override
    def extract(self, output_schema: Schema) -> Message:
        """Extract data from MongoDB database.

        Args:
            output_schema: WCT schema for data validation

        Returns:
            Message containing extracted data in WCF schema format

        Raises:
            ConnectorExtractionError: If extraction fails or schema unsupported

        """
        # Validate output schema
        if not any(
            s.name == output_schema.name and s.version == output_schema.version
            for s in _SUPPORTED_OUTPUT_SCHEMAS
        ):
            raise ConnectorExtractionError(
                f"Unsupported output schema: {output_schema.name} {output_schema.version}"
            )

        try:
            client: MongoClient[MongoDocument] = MongoClient(self._config.uri)
            db: Database[MongoDocument] = client[self._config.database]

            # Extract collection metadata
            collection_names = db.list_collection_names()
            collections_metadata: list[CollectionMetadata] = []
            data_items: list[StandardInputDataItemModel[DocumentDatabaseMetadata]] = []

            for collection_name in collection_names:
                collection: Collection[MongoDocument] = db[collection_name]
                doc_count = collection.estimated_document_count()

                collections_metadata.append(
                    CollectionMetadata(
                        name=collection_name,
                        document_count=doc_count,
                    )
                )

                # Sample documents from collection
                documents: list[MongoDocument] = list(
                    collection.find().limit(self._config.sample_size)
                )

                for doc in documents:
                    # Extract data items from document fields
                    doc_items = self._extract_document_fields(doc, collection_name)
                    data_items.extend(doc_items)

            # Build typed metadata and config for producer
            extraction_metadata = ExtractionMetadata(collections=collections_metadata)
            producer_config = ProducerConfig(
                uri=self._config.uri,
                database=self._config.database,
                sample_size=self._config.sample_size,
            )

            # Load producer and transform data
            producer = self._load_producer(output_schema)
            content = producer.produce(
                schema_version=output_schema.version,
                metadata=extraction_metadata,
                data_items=data_items,
                config_data=producer_config,
            )

            return Message(
                id=f"MongoDB data from {self._config.database}",
                content=content,
                schema=output_schema,
            )

        except ConnectorExtractionError:
            raise
        except Exception as e:
            logger.error(f"MongoDB extraction failed: {e}")
            raise ConnectorExtractionError(str(e)) from e

    def _extract_document_fields(
        self,
        doc: MongoDocument,
        collection_name: str,
        field_prefix: str = "",
    ) -> list[StandardInputDataItemModel[DocumentDatabaseMetadata]]:
        """Extract data items from document fields, handling nested structures.

        Args:
            doc: MongoDB document
            collection_name: Name of the source collection
            field_prefix: Prefix for nested field names

        Returns:
            List of validated data items with content and metadata

        """
        data_items: list[StandardInputDataItemModel[DocumentDatabaseMetadata]] = []

        for field_name, value in doc.items():
            full_field_name = (
                f"{field_prefix}{field_name}"
                if not field_prefix
                else f"{field_prefix}.{field_name}"
            )
            if not field_prefix:
                full_field_name = field_name

            if value is None:
                # Skip null values
                continue

            if isinstance(value, str) and value == "":
                # Skip empty strings
                continue

            if isinstance(value, dict):
                # Recursively extract nested document fields
                nested_items = self._extract_document_fields(
                    cast(MongoDocument, value), collection_name, full_field_name
                )
                data_items.extend(nested_items)
            else:
                # Convert value to string (handles ObjectId, numbers, etc.)
                str_value = self._convert_to_string(value)

                metadata = DocumentDatabaseMetadata(
                    source=f"mongodb_{self._config.database}_{collection_name}_{full_field_name}",
                    connector_type=_CONNECTOR_NAME,
                    collection_name=collection_name,
                    field_name=full_field_name,
                )

                data_items.append(
                    StandardInputDataItemModel(
                        content=str_value,
                        metadata=metadata,
                    )
                )

        return data_items

    def _convert_to_string(self, value: object) -> str:
        """Convert a value to string representation.

        Handles special MongoDB types like ObjectId.

        Args:
            value: Value to convert

        Returns:
            String representation of the value

        """
        if isinstance(value, ObjectId):
            return str(value)
        return str(value)
