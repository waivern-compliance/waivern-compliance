"""Tests for standard_input v1.0.0 schema producer."""

import pytest
from waivern_core.schemas import (
    DocumentDatabaseMetadata,
    StandardInputDataItemModel,
)

from waivern_mongodb.connector import (
    CollectionMetadata,
    ExtractionMetadata,
    ProducerConfig,
)
from waivern_mongodb.schema_producers import standard_input_1_0_0


@pytest.fixture
def sample_metadata() -> ExtractionMetadata:
    """Sample MongoDB metadata for tests."""
    return ExtractionMetadata(
        collections=[
            CollectionMetadata(name="users", document_count=100),
            CollectionMetadata(name="orders", document_count=50),
        ]
    )


@pytest.fixture
def sample_data_items() -> list[StandardInputDataItemModel[DocumentDatabaseMetadata]]:
    """Sample data items for tests."""
    return [
        StandardInputDataItemModel(
            content="john@example.com",
            metadata=DocumentDatabaseMetadata(
                source="mongodb_test_db_users_email",
                connector_type="mongodb",
                collection_name="users",
                field_name="email",
            ),
        ),
        StandardInputDataItemModel(
            content="Jane Doe",
            metadata=DocumentDatabaseMetadata(
                source="mongodb_test_db_users_name",
                connector_type="mongodb",
                collection_name="users",
                field_name="name",
            ),
        ),
    ]


@pytest.fixture
def sample_config_data() -> ProducerConfig:
    """Sample config data for tests."""
    return ProducerConfig(
        uri="mongodb://localhost:27017",
        database="test_db",
        sample_size=100,
    )


class TestStandardInputProducer:
    """Tests for the standard_input schema producer."""

    def test_produce_returns_correct_schema_version(
        self,
        sample_metadata: ExtractionMetadata,
        sample_data_items: list[StandardInputDataItemModel[DocumentDatabaseMetadata]],
        sample_config_data: ProducerConfig,
    ) -> None:
        """Produced output includes the correct schemaVersion."""
        result = standard_input_1_0_0.produce(
            schema_version="1.0.0",
            metadata=sample_metadata,
            data_items=sample_data_items,
            config_data=sample_config_data,
        )

        assert result["schemaVersion"] == "1.0.0"

    def test_produce_includes_database_name_in_name_field(
        self,
        sample_metadata: ExtractionMetadata,
        sample_data_items: list[StandardInputDataItemModel[DocumentDatabaseMetadata]],
        sample_config_data: ProducerConfig,
    ) -> None:
        """Produced output includes database name in the name field."""
        result = standard_input_1_0_0.produce(
            schema_version="1.0.0",
            metadata=sample_metadata,
            data_items=sample_data_items,
            config_data=sample_config_data,
        )

        assert result["name"] == "mongodb_text_from_test_db"

    def test_produce_includes_source_uri(
        self,
        sample_metadata: ExtractionMetadata,
        sample_data_items: list[StandardInputDataItemModel[DocumentDatabaseMetadata]],
        sample_config_data: ProducerConfig,
    ) -> None:
        """Produced output includes the MongoDB URI as source."""
        result = standard_input_1_0_0.produce(
            schema_version="1.0.0",
            metadata=sample_metadata,
            data_items=sample_data_items,
            config_data=sample_config_data,
        )

        assert result["source"] == "mongodb://localhost:27017/test_db"

    def test_produce_includes_metadata_with_collection_info(
        self,
        sample_metadata: ExtractionMetadata,
        sample_data_items: list[StandardInputDataItemModel[DocumentDatabaseMetadata]],
        sample_config_data: ProducerConfig,
    ) -> None:
        """Produced output metadata includes collection information."""
        result = standard_input_1_0_0.produce(
            schema_version="1.0.0",
            metadata=sample_metadata,
            data_items=sample_data_items,
            config_data=sample_config_data,
        )

        metadata = result["metadata"]
        assert metadata["connector_type"] == "mongodb"
        assert metadata["connection_info"]["uri"] == "mongodb://localhost:27017"
        assert metadata["connection_info"]["database"] == "test_db"
        assert len(metadata["collections"]) == 2
        assert metadata["total_data_items"] == 2

    def test_produce_includes_data_items(
        self,
        sample_metadata: ExtractionMetadata,
        sample_data_items: list[StandardInputDataItemModel[DocumentDatabaseMetadata]],
        sample_config_data: ProducerConfig,
    ) -> None:
        """Produced output includes the data items array."""
        result = standard_input_1_0_0.produce(
            schema_version="1.0.0",
            metadata=sample_metadata,
            data_items=sample_data_items,
            config_data=sample_config_data,
        )

        assert "data" in result
        assert len(result["data"]) == 2
        assert result["data"][0]["content"] == "john@example.com"

    def test_produce_handles_empty_data_items(
        self,
        sample_metadata: ExtractionMetadata,
        sample_config_data: ProducerConfig,
    ) -> None:
        """Produced output handles empty data items array gracefully."""
        result = standard_input_1_0_0.produce(
            schema_version="1.0.0",
            metadata=sample_metadata,
            data_items=[],
            config_data=sample_config_data,
        )

        assert result["data"] == []
        assert result["metadata"]["total_data_items"] == 0
