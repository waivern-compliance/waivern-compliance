"""Tests for schema base classes and utilities."""

from typing import Any
from unittest.mock import Mock

import pytest

from wct.schemas.base import JsonSchemaLoader, SchemaLoader


class MockSchema:
    """Mock schema for testing that follows Schema interface."""

    _VERSION = "1.0.0"

    def __init__(self, loader: SchemaLoader | None = None) -> None:
        """Initialize with optional loader."""
        self._loader = loader or JsonSchemaLoader()

    @property
    def name(self) -> str:
        """Return schema name."""
        return "mock_schema"

    @property
    def version(self) -> str:
        """Return schema version."""
        return self._VERSION

    @property
    def schema(self) -> dict[str, Any]:
        """Return schema definition."""
        return self._loader.load(self.name, self.version)


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

        try:
            # First load should read from file
            result1 = loader.load("standard_input", "1.0.0")
            assert isinstance(result1, dict)
            assert "type" in result1 or "$schema" in result1

            # Second load should use cache (we can't directly test this without
            # accessing internals, but at least we verify it doesn't fail)
            result2 = loader.load("standard_input", "1.0.0")
            assert result1 == result2
        except FileNotFoundError:
            # If schema files don't exist in test environment, skip
            pytest.skip("Real schema files not available in test environment")

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

        try:
            # Load schema and verify the version in the JSON matches what we requested
            result = loader.load("standard_input", "1.0.0")
            assert result["version"] == "1.0.0"
        except FileNotFoundError:
            pytest.skip("Schema file not found - acceptable in test environment")


class TestSchemaImplementation:
    """Tests for Schema base class."""

    def test_mock_schema_properties(self) -> None:
        """Test schema properties."""
        mock_loader = Mock(spec=SchemaLoader)
        mock_loader.load.return_value = {"test": "schema"}

        schema = MockSchema(mock_loader)

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
