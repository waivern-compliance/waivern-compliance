"""Tests for StandardInputSchema."""

import dataclasses

import pytest
from pydantic import ValidationError
from waivern_core.schemas import (
    BaseMetadata,
    FilesystemMetadata,
    RelationalDatabaseMetadata,
    StandardInputDataItemModel,
    StandardInputDataModel,
    StandardInputSchema,
)

# Version constant for easy maintenance
EXPECTED_VERSION = "1.0.0"


class TestStandardInputSchema:
    """Tests for StandardInputSchema."""

    def test_init_creates_working_schema(self) -> None:
        """Test initialization creates a working schema instance."""
        schema = StandardInputSchema()
        # Test that the schema instance has the expected public interface
        assert hasattr(schema, "name")
        assert hasattr(schema, "version")
        assert hasattr(schema, "schema")
        # Test that the properties are actually accessible
        assert isinstance(schema.name, str)
        assert isinstance(schema.version, str)

    def test_name_property(self) -> None:
        """Test name property returns correct value."""
        schema = StandardInputSchema()
        assert schema.name == "standard_input"

    def test_correct_version_is_loaded(self) -> None:
        """Test version property returns correct value."""
        schema = StandardInputSchema()
        assert schema.version == EXPECTED_VERSION

    def test_schema_property_returns_dict(self) -> None:
        """Test that schema property returns a dictionary structure."""
        schema = StandardInputSchema()

        result = schema.schema
        # Test that it returns a dictionary (the expected format)
        assert isinstance(result, dict)

    def test_schema_integration(self) -> None:
        """Test schema loading integration with real files."""
        schema = StandardInputSchema()

        result = schema.schema
        # Verify it's a valid schema structure
        assert isinstance(result, dict)
        assert "$schema" in result or "type" in result
        # Should have basic schema properties
        expected_keys = ["type", "properties"]
        assert any(key in result for key in expected_keys)

    def test_schema_immutability(self) -> None:
        """Test that schema instances behave as immutable objects."""
        schema = StandardInputSchema()

        # Test that core properties return consistent values
        name1 = schema.name
        name2 = schema.name
        assert name1 == name2 == "standard_input"

        version1 = schema.version
        version2 = schema.version
        assert version1 == version2 == EXPECTED_VERSION

        # Verify it's a dataclass (public API)
        assert dataclasses.is_dataclass(schema)


class TestGenericStandardInputModel:
    def test_works_with_base_metadata(self) -> None:
        item = StandardInputDataItemModel[BaseMetadata](
            content="test content",
            metadata=BaseMetadata(source="test", connector_type="generic"),
        )

        assert item.content == "test content"
        assert item.metadata.source == "test"
        assert item.metadata.connector_type == "generic"

    def test_works_with_relational_database_metadata(self) -> None:
        item = StandardInputDataItemModel[RelationalDatabaseMetadata](
            content="john@example.com",
            metadata=RelationalDatabaseMetadata(
                source="db_source",
                connector_type="mysql",
                table_name="users",
                column_name="email",
                schema_name="public",
            ),
        )

        assert item.metadata.table_name == "users"
        assert item.metadata.column_name == "email"

    def test_works_with_filesystem_metadata(self) -> None:
        item = StandardInputDataItemModel[FilesystemMetadata](
            content="file content",
            metadata=FilesystemMetadata(
                source="file_source",
                connector_type="filesystem",
                file_path="/path/to/file.txt",
            ),
        )

        assert item.metadata.file_path == "/path/to/file.txt"

    def test_full_data_model_with_typed_metadata(self) -> None:
        data_model = StandardInputDataModel[RelationalDatabaseMetadata](
            schemaVersion="1.0.0",
            name="test_data",
            data=[
                StandardInputDataItemModel[RelationalDatabaseMetadata](
                    content="test@example.com",
                    metadata=RelationalDatabaseMetadata(
                        source="test_db",
                        connector_type="mysql",
                        table_name="users",
                        column_name="email",
                        schema_name="public",
                    ),
                )
            ],
        )

        assert len(data_model.data) == 1
        assert data_model.data[0].metadata.table_name == "users"


class TestBaseMetadata:
    def test_valid_creation(self) -> None:
        metadata = BaseMetadata(source="test_source", connector_type="test_type")
        assert metadata.source == "test_source"
        assert metadata.connector_type == "test_type"

    def test_requires_source(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            BaseMetadata(connector_type="test")  # type: ignore[call-arg]
        assert "source" in str(exc_info.value)

    def test_requires_connector_type(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            BaseMetadata(source="test")  # type: ignore[call-arg]
        assert "connector_type" in str(exc_info.value)


class TestRelationalDatabaseMetadata:
    def test_valid_creation(self) -> None:
        metadata = RelationalDatabaseMetadata(
            source="db_source",
            connector_type="mysql",
            table_name="users",
            column_name="email",
            schema_name="public",
        )
        assert metadata.table_name == "users"
        assert metadata.column_name == "email"
        assert metadata.schema_name == "public"

    def test_requires_database_fields(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            RelationalDatabaseMetadata(source="db", connector_type="mysql")  # type: ignore[call-arg]
        error_msg = str(exc_info.value)
        assert "table_name" in error_msg
        assert "column_name" in error_msg
        assert "schema_name" in error_msg


class TestFilesystemMetadata:
    def test_valid_creation(self) -> None:
        metadata = FilesystemMetadata(
            source="file_source",
            connector_type="filesystem",
            file_path="/path/to/file.txt",
        )
        assert metadata.file_path == "/path/to/file.txt"

    def test_requires_file_path(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            FilesystemMetadata(source="file", connector_type="filesystem")  # type: ignore[call-arg]
        assert "file_path" in str(exc_info.value)
