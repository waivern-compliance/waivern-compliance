"""Tests for schema base classes and utilities."""

import pickle
from pathlib import Path

import pytest
from pydantic import BaseModel

from waivern_core.schemas import (
    JsonSchemaLoader,
    Schema,
    SchemaLoader,
    SchemaLoadError,
    SchemaRegistry,
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


class TestSchemaDependencyInjection:
    """Tests for Schema loader behaviour (singleton vs injected)."""

    def test_default_schemas_share_singleton_loader_cache(self) -> None:
        """Multiple Schema instances without custom loader share singleton loader.

        This verifies that the singleton pattern still works for the default case,
        ensuring efficient cache sharing across all Schema instances.
        """
        # Create two different Schema instances (different schemas)
        schema1 = Schema("standard_input", "1.0.0")
        schema2 = Schema("standard_input", "1.0.0")

        # Access schema definitions to trigger loading
        json_schema1 = schema1.schema
        json_schema2 = schema2.schema

        # Should be same cached object from singleton loader's cache
        assert json_schema1 is json_schema2

        # Verify they both loaded successfully
        assert json_schema1["version"] == "1.0.0"
        assert json_schema2["version"] == "1.0.0"

    def test_schema_with_custom_loader_uses_injected_loader(self) -> None:
        """Schema with injected loader uses it instead of singleton.

        This verifies dependency injection works - useful for testing or
        alternative schema sources.
        """
        # Create custom loader pointing to test fixtures
        fixtures_path = Path(__file__).parent / "fixtures"
        custom_loader = JsonSchemaLoader(search_paths=[fixtures_path])

        # Inject custom loader
        schema = Schema("test_schema", "1.0.0", loader=custom_loader)

        # Should use the injected loader (which finds version mismatch in fixture)
        with pytest.raises(SchemaLoadError) as exc_info:
            _ = schema.schema

        assert "version mismatch" in str(exc_info.value).lower()
        assert "1.0.0" in str(exc_info.value)
        assert "2.0.0" in str(exc_info.value)

    def test_custom_loader_does_not_affect_singleton(self) -> None:
        """Injecting loader into one instance doesn't affect others.

        This verifies isolation between injected and default behaviours.
        """
        # Create schema with custom loader (non-existent path)
        custom_loader = JsonSchemaLoader(search_paths=[Path("/nonexistent/path")])
        schema_with_custom = Schema("standard_input", "1.0.0", loader=custom_loader)

        # Create schema without custom loader (uses singleton)
        schema_default = Schema("standard_input", "1.0.0")

        # Custom loader should fail to find schema
        with pytest.raises(FileNotFoundError):
            _ = schema_with_custom.schema

        # Default schema should succeed (uses singleton with registry paths)
        json_schema = schema_default.schema
        assert isinstance(json_schema, dict)
        assert json_schema["version"] == "1.0.0"


class TestSchemaRegistry:
    """Tests for SchemaRegistry."""

    def test_default_search_paths_include_waivern_core(self) -> None:
        """Registry includes default waivern-core schema directory.

        Note: Other packages may have registered paths, so we verify waivern-core's
        path is present and is the first (default) path, not that it's the ONLY path.
        """
        paths = SchemaRegistry.get_search_paths()

        # At minimum, waivern-core's default path should be present
        assert len(paths) >= 1
        # First path should always be waivern-core's default
        assert paths[0].name == "json_schemas"
        assert "waivern_core" in str(paths[0])

    def test_register_additional_search_path(self) -> None:
        """Users can register additional schema directories."""
        custom_path = Path("/custom/schemas")

        initial_count = len(SchemaRegistry.get_search_paths())
        SchemaRegistry.register_search_path(custom_path)
        paths = SchemaRegistry.get_search_paths()

        # Should have one more path than before
        assert len(paths) == initial_count + 1
        assert custom_path in paths

    def test_register_duplicate_path_ignored(self) -> None:
        """Registering the same path twice doesn't create duplicates."""
        custom_path = Path("/custom/schemas")

        initial_count = len(SchemaRegistry.get_search_paths())
        SchemaRegistry.register_search_path(custom_path)
        SchemaRegistry.register_search_path(custom_path)
        paths = SchemaRegistry.get_search_paths()

        # Should only add one path, not two
        assert len(paths) == initial_count + 1
        assert paths.count(custom_path) == 1

    def test_get_search_paths_returns_copy(self) -> None:
        """get_search_paths returns a copy to prevent external modification."""
        paths1 = SchemaRegistry.get_search_paths()
        paths2 = SchemaRegistry.get_search_paths()

        # Modifying returned list shouldn't affect registry
        original_len = len(paths2)
        paths1.append(Path("/external/modification"))

        assert paths1 != paths2
        assert len(paths2) == original_len  # Unchanged

    def test_clear_search_paths_removes_all(self) -> None:
        """clear_search_paths removes all paths including defaults."""
        SchemaRegistry.register_search_path(Path("/custom1"))
        SchemaRegistry.register_search_path(Path("/custom2"))

        SchemaRegistry.clear_search_paths()
        # After clear, get_search_paths should reinitialise with defaults
        paths = SchemaRegistry.get_search_paths()

        assert len(paths) == 1  # Only default after reinitialisation
        assert "waivern_core" in str(paths[0])

    def test_schema_uses_registry_paths(self) -> None:
        """Schema class queries registry for search paths."""
        # Create schema (should use registry paths)
        schema = Schema("standard_input", "1.0.0")

        # Should successfully load from default registry path
        json_schema = schema.schema
        assert isinstance(json_schema, dict)
        assert json_schema["version"] == "1.0.0"


class TestSchemaSerialisation:
    """Tests for Schema serialisation (pickle and Pydantic)."""

    def test_pickle_round_trip(self) -> None:
        """Schema can be pickled and unpickled correctly."""
        original = Schema("standard_input", "1.0.0")

        pickled = pickle.dumps(original)
        restored = pickle.loads(pickled)  # noqa: S301

        assert restored.name == original.name
        assert restored.version == original.version
        assert restored == original

    def test_pickled_schema_can_load_definition(self) -> None:
        """Unpickled Schema can still load its JSON schema definition."""
        original = Schema("standard_input", "1.0.0")
        # Trigger lazy loading before pickling
        _ = original.schema

        pickled = pickle.dumps(original)
        restored = pickle.loads(pickled)  # noqa: S301

        # Restored schema can still load definition
        assert restored.schema["version"] == "1.0.0"

    def test_pydantic_model_with_schema_field(self) -> None:
        """Schema can be used as a field in Pydantic models."""

        class TestModel(BaseModel):
            schema_ref: Schema

        model = TestModel(schema_ref=Schema("standard_input", "1.0.0"))

        assert model.schema_ref.name == "standard_input"
        assert model.schema_ref.version == "1.0.0"

    def test_pydantic_serialisation_round_trip(self) -> None:
        """Schema in Pydantic model serialises and deserialises correctly."""

        class TestModel(BaseModel):
            schema_ref: Schema

        original = TestModel(schema_ref=Schema("standard_input", "1.0.0"))

        data = original.model_dump()
        restored = TestModel.model_validate(data)

        assert restored.schema_ref.name == "standard_input"
        assert restored.schema_ref.version == "1.0.0"

    def test_pydantic_optional_schema_field(self) -> None:
        """Optional Schema field works in Pydantic models."""

        class TestModel(BaseModel):
            schema_ref: Schema | None = None

        # With None
        model_none = TestModel()
        assert model_none.schema_ref is None

        # With Schema
        model_with = TestModel(schema_ref=Schema("standard_input", "1.0.0"))
        assert model_with.schema_ref is not None
        assert model_with.schema_ref.name == "standard_input"

        # Round-trip with None
        restored_none = TestModel.model_validate(model_none.model_dump())
        assert restored_none.schema_ref is None

        # Round-trip with Schema
        restored_with = TestModel.model_validate(model_with.model_dump())
        assert restored_with.schema_ref is not None
        assert restored_with.schema_ref.name == "standard_input"
