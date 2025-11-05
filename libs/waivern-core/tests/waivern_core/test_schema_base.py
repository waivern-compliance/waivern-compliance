"""Tests for schema base classes and utilities."""

from pathlib import Path

import pytest

from waivern_core.schemas.base import (
    JsonSchemaLoader,
    Schema,
    SchemaLoader,
    SchemaLoadError,
)


class TestJsonSchemaLoader:
    """Tests for JsonSchemaLoader."""

    def test_init(self) -> None:
        """Test loader initialization."""
        loader = JsonSchemaLoader()
        # We can't test private properties, so just verify the loader works
        assert hasattr(loader, "load")
        assert callable(loader.load)

    def test_load_from_file_and_cache(self) -> None:
        """Test loading from file and caching behavior using real schema files."""
        loader = JsonSchemaLoader()

        # First load should read from file
        result1 = loader.load("standard_input", "1.0.0")
        assert isinstance(result1, dict)
        assert "type" in result1 or "$schema" in result1

        # Second load should use cache (we can't directly test this without
        # accessing internals, but at least we verify it doesn't fail)
        result2 = loader.load("standard_input", "1.0.0")
        assert result1 == result2

    def test_load_file_not_found(self) -> None:
        """Test FileNotFoundError when schema file doesn't exist."""
        loader = JsonSchemaLoader()

        with pytest.raises(FileNotFoundError) as exc_info:
            loader.load("nonexistent_schema", "1.0.0")

        assert "Schema file for 'nonexistent_schema' version '1.0.0' not found" in str(
            exc_info.value
        )

    def test_load_nonexistent_version(self) -> None:
        """Test FileNotFoundError when both schema and version don't exist."""
        loader = JsonSchemaLoader()

        with pytest.raises(FileNotFoundError) as exc_info:
            loader.load("definitely_nonexistent_schema", "99.99.99")

        assert (
            "Schema file for 'definitely_nonexistent_schema' version '99.99.99' not found"
            in str(exc_info.value)
        )

    def test_version_number_match(self) -> None:
        """Test that loaded schema version matches requested version."""
        loader = JsonSchemaLoader()

        # Load schema and verify the version in the JSON matches what we requested
        result = loader.load("standard_input", "1.0.0")
        assert result["version"] == "1.0.0"

    def test_loader_finds_schema_in_package_relative_path(self) -> None:
        """Test that loader finds schemas in package-relative path."""
        # Default loader should search package-relative paths first
        loader = JsonSchemaLoader()

        # standard_input schema is in package-relative location:
        # libs/waivern-core/src/waivern_core/schemas/json_schemas/standard_input/1.0.0/
        result = loader.load("standard_input", "1.0.0")

        assert isinstance(result, dict)
        assert "type" in result or "$schema" in result
        assert result["version"] == "1.0.0"
        assert "properties" in result

    def test_custom_search_paths_override_defaults(self) -> None:
        """Test that custom search paths override default search paths."""
        # Create a loader with custom search paths
        custom_path = Path(__file__).parent / "fixtures"
        loader = JsonSchemaLoader(search_paths=[custom_path])

        # Should look in custom path only, not default package-relative paths
        with pytest.raises(FileNotFoundError) as exc_info:
            loader.load("standard_input", "1.0.0")

        # Verify error message shows it looked for the schema
        error_message = str(exc_info.value)
        assert "standard_input" in error_message
        assert "1.0.0" in error_message


class TestSchemaCreation:
    """Tests for creating Schema instances."""

    def test_create_schema_with_name_and_version(self) -> None:
        """Users can create a schema by providing name and version."""
        schema = Schema("standard_input", "1.0.0")
        assert schema.name == "standard_input"
        assert schema.version == "1.0.0"

    def test_create_multiple_schemas(self) -> None:
        """Users can create multiple different schemas."""
        schema1 = Schema("standard_input", "1.0.0")
        schema2 = Schema("personal_data_finding", "1.0.0")
        schema3 = Schema("standard_input", "1.1.0")

        assert schema1.name == "standard_input"
        assert schema2.name == "personal_data_finding"
        assert schema3.version == "1.1.0"


class TestSchemaEquality:
    """Tests for schema equality comparison."""

    def test_schemas_with_same_name_and_version_are_equal(self) -> None:
        """Two schemas with identical name and version should be equal."""
        schema1 = Schema("standard_input", "1.0.0")
        schema2 = Schema("standard_input", "1.0.0")
        assert schema1 == schema2

    def test_schemas_with_different_names_are_not_equal(self) -> None:
        """Schemas with different names should not be equal."""
        schema1 = Schema("standard_input", "1.0.0")
        schema2 = Schema("personal_data_finding", "1.0.0")
        assert schema1 != schema2

    def test_schemas_with_different_versions_are_not_equal(self) -> None:
        """Schemas with same name but different versions should not be equal."""
        schema1 = Schema("standard_input", "1.0.0")
        schema2 = Schema("standard_input", "1.1.0")
        assert schema1 != schema2

    def test_schema_not_equal_to_non_schema(self) -> None:
        """Schema should not be equal to non-Schema objects."""
        schema = Schema("standard_input", "1.0.0")
        assert schema != "standard_input"
        assert schema != {"name": "standard_input", "version": "1.0.0"}
        assert schema != None


class TestSchemaHashing:
    """Tests for schema hashing and use in collections."""

    def test_schemas_can_be_used_in_sets(self) -> None:
        """Users can store schemas in sets."""
        schema1 = Schema("standard_input", "1.0.0")
        schema2 = Schema("personal_data_finding", "1.0.0")
        schema3 = Schema("standard_input", "1.0.0")  # Duplicate

        schema_set = {schema1, schema2, schema3}
        assert len(schema_set) == 2
        assert schema1 in schema_set
        assert schema2 in schema_set

    def test_schemas_can_be_used_as_dict_keys(self) -> None:
        """Users can use schemas as dictionary keys."""
        schema1 = Schema("standard_input", "1.0.0")
        schema2 = Schema("personal_data_finding", "1.0.0")
        schema3 = Schema("standard_input", "1.0.0")  # Duplicate

        schema_dict = {
            schema1: "input_handler",
            schema2: "finding_processor",
        }

        # Update with duplicate key should replace value
        schema_dict[schema3] = "updated_handler"

        assert len(schema_dict) == 2
        assert schema_dict[schema1] == "updated_handler"
        assert schema_dict[schema2] == "finding_processor"
        assert schema_dict[schema3] == "updated_handler"


class TestSchemaJsonLoading:
    """Tests for accessing JSON schema definitions through Schema."""

    def test_access_json_schema_definition(self) -> None:
        """Users can access the JSON schema definition for validation."""
        schema = Schema("standard_input", "1.0.0")

        # Access schema property - should load JSON file
        json_schema = schema.schema

        # Verify it's a valid JSON schema definition
        assert isinstance(json_schema, dict)
        assert json_schema["version"] == "1.0.0"
        assert "properties" in json_schema
        assert "$schema" in json_schema  # JSON Schema draft marker

        # Subsequent access should return cached version (same object)
        json_schema2 = schema.schema
        assert json_schema is json_schema2


class TestSchemaErrorHandling:
    """Tests for error handling in Schema."""

    def test_error_for_nonexistent_schema(self) -> None:
        """Users get clear error when schema file doesn't exist."""
        schema = Schema("nonexistent_schema", "1.0.0")

        with pytest.raises(FileNotFoundError) as exc_info:
            _ = schema.schema

        assert "nonexistent_schema" in str(exc_info.value)
        assert "1.0.0" in str(exc_info.value)

    def test_error_for_schema_version_mismatch(self) -> None:
        """Users get clear error when JSON schema version doesn't match parameter.

        This test uses a fixture file (fixtures/test_schema/1.0.0/test_schema.json)
        that contains version "2.0.0" in the JSON, creating a mismatch with the
        directory structure version "1.0.0".
        """
        # Create loader with custom search path pointing to fixtures
        fixtures_path = Path(__file__).parent / "fixtures"
        loader = JsonSchemaLoader(search_paths=[fixtures_path])

        # The fixture file has version "2.0.0" in JSON but is in 1.0.0 directory
        with pytest.raises(SchemaLoadError) as exc_info:
            loader.load("test_schema", "1.0.0")

        assert "version mismatch" in str(exc_info.value).lower()
        assert "1.0.0" in str(exc_info.value)
        assert "2.0.0" in str(exc_info.value)


class TestSchemaStringRepresentation:
    """Tests for schema string representation."""

    def test_repr_is_readable(self) -> None:
        """Users get helpful string representation for debugging."""
        schema = Schema("standard_input", "1.0.0")

        repr_str = repr(schema)

        # Should contain schema name and version
        assert "Schema" in repr_str
        assert "standard_input" in repr_str
        assert "1.0.0" in repr_str

        # Should be in the format: Schema(name='...', version='...')
        assert repr_str == "Schema(name='standard_input', version='1.0.0')"


class TestSchemaLoader:
    """Tests for SchemaLoader protocol."""

    def test_protocol_compliance(self) -> None:
        """Test that JsonSchemaLoader implements SchemaLoader protocol."""
        loader = JsonSchemaLoader()
        assert isinstance(loader, SchemaLoader)

        # Test method signature
        assert hasattr(loader, "load")
        assert callable(loader.load)
