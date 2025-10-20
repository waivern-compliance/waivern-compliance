"""Tests for schema base classes and utilities."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, override
from unittest.mock import Mock

import pytest

from waivern_core.schemas.base import JsonSchemaLoader, Schema, SchemaLoader


@dataclass(frozen=True, slots=True)
class MockSchema(Schema):
    """Mock schema for testing that inherits from Schema base class."""

    schema_name: str = "mock_schema"
    schema_version: str = "1.0.0"
    loader: SchemaLoader = field(default_factory=JsonSchemaLoader)

    @property
    @override
    def name(self) -> str:
        """Return schema name."""
        return self.schema_name

    @property
    @override
    def version(self) -> str:
        """Return schema version."""
        return self.schema_version

    @property
    @override
    def schema(self) -> dict[str, Any]:
        """Return schema definition."""
        return self.loader.load(self.name, self.version)


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

        # Should look in custom path only, not default package-relative or WCT paths
        with pytest.raises(FileNotFoundError) as exc_info:
            loader.load("standard_input", "1.0.0")

        # Verify error message shows it looked for the schema
        error_message = str(exc_info.value)
        assert "standard_input" in error_message
        assert "1.0.0" in error_message


class TestSchemaImplementation:
    """Tests for Schema base class."""

    def test_mock_schema_properties(self) -> None:
        """Test schema properties."""
        mock_loader = Mock(spec=SchemaLoader)
        mock_loader.load.return_value = {"test": "schema"}

        schema = MockSchema(loader=mock_loader)

        assert schema.name == "mock_schema"
        assert schema.version == "1.0.0"

        # Test schema property calls loader
        result = schema.schema
        assert result == {"test": "schema"}
        mock_loader.load.assert_called_once_with("mock_schema", "1.0.0")


class TestSchemaLoader:
    """Tests for SchemaLoader protocol."""

    def test_protocol_compliance(self) -> None:
        """Test that JsonSchemaLoader implements SchemaLoader protocol."""
        loader = JsonSchemaLoader()
        assert isinstance(loader, SchemaLoader)

        # Test method signature
        assert hasattr(loader, "load")
        assert callable(loader.load)
