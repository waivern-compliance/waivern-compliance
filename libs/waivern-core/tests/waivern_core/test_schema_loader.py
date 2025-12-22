"""Tests for schema loading infrastructure.

For Schema value object tests, see test_schema.py.
For serialisation tests, see test_schema_serialisation.py.
"""

from pathlib import Path

import pytest

from waivern_core.schemas import (
    JsonSchemaLoader,
    Schema,
    SchemaLoader,
    SchemaLoadError,
    SchemaRegistry,
)

# =============================================================================
# JSON Schema Loader
# =============================================================================


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


# =============================================================================
# Schema Loader Protocol
# =============================================================================


class TestSchemaLoader:
    """Tests for SchemaLoader protocol."""

    def test_protocol_compliance(self) -> None:
        """Test that JsonSchemaLoader implements SchemaLoader protocol."""
        loader = JsonSchemaLoader()
        assert isinstance(loader, SchemaLoader)

        # Test method signature
        assert hasattr(loader, "load")
        assert callable(loader.load)


# =============================================================================
# Dependency Injection
# =============================================================================


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


# =============================================================================
# Schema Registry
# =============================================================================


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
