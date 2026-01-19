"""Tests for MongoDB connector extraction."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId
from waivern_core import Schema
from waivern_core.errors import ConnectorConfigError, ConnectorExtractionError

from waivern_mongodb import MongoDBConnector, MongoDBConnectorConfig

MONGODB_ENV_VARS = ["MONGODB_URI", "MONGODB_DATABASE"]


@pytest.fixture
def clean_mongodb_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Clear MongoDB environment variables for test isolation."""
    for var in MONGODB_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


@pytest.fixture
def test_config(clean_mongodb_env: pytest.MonkeyPatch) -> MongoDBConnectorConfig:
    """Create a test configuration."""
    return MongoDBConnectorConfig.from_properties(
        {
            "uri": "mongodb://localhost:27017",
            "database": "test_db",
            "sample_size": 10,
        }
    )


class TestMongoDBConnectorMetadata:
    """Tests for connector class metadata methods."""

    def test_get_name_returns_mongodb(self) -> None:
        """get_name returns 'mongodb' as the connector identifier."""
        assert MongoDBConnector.get_name() == "mongodb"

    def test_get_supported_output_schemas_returns_standard_input(self) -> None:
        """get_supported_output_schemas returns standard_input v1.0.0."""
        schemas = MongoDBConnector.get_supported_output_schemas()

        assert len(schemas) == 1
        assert schemas[0].name == "standard_input"
        assert schemas[0].version == "1.0.0"


class TestMongoDBConnectorExtraction:
    """Tests for MongoDB data extraction."""

    @pytest.fixture
    def mock_mongo_client(self) -> Generator[MagicMock, None, None]:
        """Create a mock MongoDB client."""
        with patch("waivern_mongodb.connector.MongoClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            yield mock_client

    def test_extract_returns_message_with_correct_schema(
        self, test_config: MongoDBConnectorConfig, mock_mongo_client: MagicMock
    ) -> None:
        """Extract returns a Message with the requested output schema."""
        # Setup mock database with empty collections
        mock_db = MagicMock()
        mock_db.list_collection_names.return_value = []
        mock_mongo_client.__getitem__.return_value = mock_db

        connector = MongoDBConnector(test_config)
        result = connector.extract(Schema("standard_input", "1.0.0"))

        assert result.schema is not None
        assert result.schema.name == "standard_input"
        assert result.schema.version == "1.0.0"

    def test_extract_includes_collection_metadata(
        self, test_config: MongoDBConnectorConfig, mock_mongo_client: MagicMock
    ) -> None:
        """Extracted data includes collection names and document counts."""
        mock_db = MagicMock()
        mock_db.list_collection_names.return_value = ["patients", "appointments"]

        # Mock collections with document counts
        mock_patients = MagicMock()
        mock_patients.estimated_document_count.return_value = 100
        mock_patients.find.return_value.limit.return_value = []

        mock_appointments = MagicMock()
        mock_appointments.estimated_document_count.return_value = 50
        mock_appointments.find.return_value.limit.return_value = []

        mock_db.__getitem__.side_effect = lambda name: {  # type: ignore[reportUnknownLambdaType]
            "patients": mock_patients,
            "appointments": mock_appointments,
        }[name]
        mock_mongo_client.__getitem__.return_value = mock_db

        connector = MongoDBConnector(test_config)
        result = connector.extract(Schema("standard_input", "1.0.0"))

        # Check metadata contains collection info
        metadata = result.content.get("metadata", {})
        collections = metadata.get("collections", [])
        assert len(collections) == 2
        assert any(
            c["name"] == "patients" and c["document_count"] == 100 for c in collections
        )
        assert any(
            c["name"] == "appointments" and c["document_count"] == 50
            for c in collections
        )

    def test_extract_samples_documents_from_collections(
        self, test_config: MongoDBConnectorConfig, mock_mongo_client: MagicMock
    ) -> None:
        """Extract retrieves sample documents from each collection."""
        mock_db = MagicMock()
        mock_db.list_collection_names.return_value = ["users"]

        mock_collection = MagicMock()
        mock_collection.estimated_document_count.return_value = 5
        mock_collection.find.return_value.limit.return_value = [
            {"_id": ObjectId(), "name": "John", "email": "john@example.com"},
            {"_id": ObjectId(), "name": "Jane", "email": "jane@example.com"},
        ]
        mock_db.__getitem__.return_value = mock_collection
        mock_mongo_client.__getitem__.return_value = mock_db

        connector = MongoDBConnector(test_config)
        result = connector.extract(Schema("standard_input", "1.0.0"))

        # Should have data items from the documents
        data = result.content.get("data", [])
        assert len(data) > 0

    def test_extract_respects_sample_size_limit(
        self, clean_mongodb_env: pytest.MonkeyPatch, mock_mongo_client: MagicMock
    ) -> None:
        """Extract limits documents per collection to configured sample_size."""
        config = MongoDBConnectorConfig.from_properties(
            {
                "uri": "mongodb://localhost:27017",
                "database": "test_db",
                "sample_size": 5,
            }
        )

        mock_db = MagicMock()
        mock_db.list_collection_names.return_value = ["large_collection"]

        mock_collection = MagicMock()
        mock_collection.estimated_document_count.return_value = 1000
        mock_db.__getitem__.return_value = mock_collection
        mock_mongo_client.__getitem__.return_value = mock_db

        connector = MongoDBConnector(config)
        connector.extract(Schema("standard_input", "1.0.0"))

        # Verify limit was called with sample_size
        mock_collection.find.return_value.limit.assert_called_with(5)

    def test_extract_converts_objectid_to_string(
        self, test_config: MongoDBConnectorConfig, mock_mongo_client: MagicMock
    ) -> None:
        """MongoDB ObjectId values are converted to strings for serialisation."""
        test_id = ObjectId()
        mock_db = MagicMock()
        mock_db.list_collection_names.return_value = ["items"]

        mock_collection = MagicMock()
        mock_collection.estimated_document_count.return_value = 1
        mock_collection.find.return_value.limit.return_value = [
            {"_id": test_id, "ref_id": test_id}
        ]
        mock_db.__getitem__.return_value = mock_collection
        mock_mongo_client.__getitem__.return_value = mock_db

        connector = MongoDBConnector(test_config)
        result = connector.extract(Schema("standard_input", "1.0.0"))

        # ObjectId should be converted to string in data items
        data = result.content.get("data", [])
        for item in data:
            # Content should be string, not ObjectId
            assert isinstance(item.get("content"), str)

    def test_extract_handles_nested_documents(
        self, test_config: MongoDBConnectorConfig, mock_mongo_client: MagicMock
    ) -> None:
        """Nested document fields are handled appropriately."""
        mock_db = MagicMock()
        mock_db.list_collection_names.return_value = ["profiles"]

        mock_collection = MagicMock()
        mock_collection.estimated_document_count.return_value = 1
        mock_collection.find.return_value.limit.return_value = [
            {
                "_id": ObjectId(),
                "user": {"name": "John", "contact": {"email": "john@example.com"}},
            }
        ]
        mock_db.__getitem__.return_value = mock_collection
        mock_mongo_client.__getitem__.return_value = mock_db

        connector = MongoDBConnector(test_config)
        result = connector.extract(Schema("standard_input", "1.0.0"))

        # Should extract nested values with field names
        data = result.content.get("data", [])
        contents = [item.get("content") for item in data]
        assert "user.name: John" in contents
        assert "user.contact.email: john@example.com" in contents

    def test_extract_handles_empty_database(
        self, test_config: MongoDBConnectorConfig, mock_mongo_client: MagicMock
    ) -> None:
        """Extract handles database with no collections gracefully."""
        mock_db = MagicMock()
        mock_db.list_collection_names.return_value = []
        mock_mongo_client.__getitem__.return_value = mock_db

        connector = MongoDBConnector(test_config)
        result = connector.extract(Schema("standard_input", "1.0.0"))

        assert result.schema is not None
        assert result.content.get("data", []) == []

    def test_extract_raises_error_on_connection_failure(
        self, test_config: MongoDBConnectorConfig
    ) -> None:
        """ConnectorExtractionError is raised when connection fails."""
        with patch("waivern_mongodb.connector.MongoClient") as mock_client_class:
            mock_client_class.side_effect = Exception("Connection refused")

            connector = MongoDBConnector(test_config)
            with pytest.raises(ConnectorExtractionError, match="Connection refused"):
                connector.extract(Schema("standard_input", "1.0.0"))

    def test_extract_raises_error_for_unsupported_schema(
        self, test_config: MongoDBConnectorConfig
    ) -> None:
        """ConnectorConfigError is raised for unsupported output schema."""
        connector = MongoDBConnector(test_config)

        with pytest.raises(ConnectorConfigError, match="Unsupported.*schema"):
            connector.extract(Schema("unsupported_schema", "1.0.0"))


class TestMongoDBConnectorDataItems:
    """Tests for granular data item extraction."""

    @pytest.fixture
    def mock_mongo_client(self) -> Generator[MagicMock, None, None]:
        """Create a mock MongoDB client."""
        with patch("waivern_mongodb.connector.MongoClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            yield mock_client

    def test_creates_data_item_for_each_field_value(
        self, test_config: MongoDBConnectorConfig, mock_mongo_client: MagicMock
    ) -> None:
        """Each document field value becomes a separate data item."""
        mock_db = MagicMock()
        mock_db.list_collection_names.return_value = ["users"]

        mock_collection = MagicMock()
        mock_collection.estimated_document_count.return_value = 1
        mock_collection.find.return_value.limit.return_value = [
            {"_id": ObjectId(), "name": "John", "email": "john@example.com", "age": 30}
        ]
        mock_db.__getitem__.return_value = mock_collection
        mock_mongo_client.__getitem__.return_value = mock_db

        connector = MongoDBConnector(test_config)
        result = connector.extract(Schema("standard_input", "1.0.0"))

        data = result.content.get("data", [])
        # Should have separate items for name, email, age (and _id)
        assert len(data) >= 3
        contents = [item.get("content") for item in data]
        assert "name: John" in contents
        assert "email: john@example.com" in contents
        assert "age: 30" in contents

    def test_data_item_metadata_includes_collection_name(
        self, test_config: MongoDBConnectorConfig, mock_mongo_client: MagicMock
    ) -> None:
        """Data item metadata includes the source collection name."""
        mock_db = MagicMock()
        mock_db.list_collection_names.return_value = ["patients"]

        mock_collection = MagicMock()
        mock_collection.estimated_document_count.return_value = 1
        mock_collection.find.return_value.limit.return_value = [
            {"_id": ObjectId(), "name": "Jane"}
        ]
        mock_db.__getitem__.return_value = mock_collection
        mock_mongo_client.__getitem__.return_value = mock_db

        connector = MongoDBConnector(test_config)
        result = connector.extract(Schema("standard_input", "1.0.0"))

        data = result.content.get("data", [])
        for item in data:
            metadata = item.get("metadata", {})
            assert metadata.get("collection_name") == "patients"

    def test_data_item_metadata_includes_field_name(
        self, test_config: MongoDBConnectorConfig, mock_mongo_client: MagicMock
    ) -> None:
        """Data item metadata includes the field name."""
        mock_db = MagicMock()
        mock_db.list_collection_names.return_value = ["users"]

        mock_collection = MagicMock()
        mock_collection.estimated_document_count.return_value = 1
        mock_collection.find.return_value.limit.return_value = [
            {"_id": ObjectId(), "email": "test@example.com"}
        ]
        mock_db.__getitem__.return_value = mock_collection
        mock_mongo_client.__getitem__.return_value = mock_db

        connector = MongoDBConnector(test_config)
        result = connector.extract(Schema("standard_input", "1.0.0"))

        data = result.content.get("data", [])
        email_item = next(
            (d for d in data if d.get("content") == "email: test@example.com"), None
        )
        assert email_item is not None
        assert email_item.get("metadata", {}).get("field_name") == "email"

    def test_skips_null_field_values(
        self, test_config: MongoDBConnectorConfig, mock_mongo_client: MagicMock
    ) -> None:
        """Null field values are not included in data items."""
        mock_db = MagicMock()
        mock_db.list_collection_names.return_value = ["users"]

        mock_collection = MagicMock()
        mock_collection.estimated_document_count.return_value = 1
        mock_collection.find.return_value.limit.return_value = [
            {"_id": ObjectId(), "name": "John", "middle_name": None}
        ]
        mock_db.__getitem__.return_value = mock_collection
        mock_mongo_client.__getitem__.return_value = mock_db

        connector = MongoDBConnector(test_config)
        result = connector.extract(Schema("standard_input", "1.0.0"))

        data = result.content.get("data", [])
        field_names = [item.get("metadata", {}).get("field_name") for item in data]
        assert "middle_name" not in field_names

    def test_skips_empty_string_values(
        self, test_config: MongoDBConnectorConfig, mock_mongo_client: MagicMock
    ) -> None:
        """Empty string values are not included in data items."""
        mock_db = MagicMock()
        mock_db.list_collection_names.return_value = ["users"]

        mock_collection = MagicMock()
        mock_collection.estimated_document_count.return_value = 1
        mock_collection.find.return_value.limit.return_value = [
            {"_id": ObjectId(), "name": "John", "nickname": ""}
        ]
        mock_db.__getitem__.return_value = mock_collection
        mock_mongo_client.__getitem__.return_value = mock_db

        connector = MongoDBConnector(test_config)
        result = connector.extract(Schema("standard_input", "1.0.0"))

        data = result.content.get("data", [])
        field_names = [item.get("metadata", {}).get("field_name") for item in data]
        assert "nickname" not in field_names
