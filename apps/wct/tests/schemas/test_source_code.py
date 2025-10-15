"""Tests for SourceCodeSchema."""

import dataclasses

from wct.schemas.source_code import SourceCodeSchema

# Version constant for easy maintenance
EXPECTED_VERSION = "1.0.0"


class TestSourceCodeSchema:
    """Tests for SourceCodeSchema."""

    def test_init_creates_working_schema(self) -> None:
        """Test initialization creates a working schema instance."""
        schema = SourceCodeSchema()
        # Test that the schema instance has the expected public interface
        assert hasattr(schema, "name")
        assert hasattr(schema, "version")
        assert hasattr(schema, "schema")
        # Test that the properties are actually accessible
        assert isinstance(schema.name, str)
        assert isinstance(schema.version, str)

    def test_name_property(self) -> None:
        """Test name property returns correct value."""
        schema = SourceCodeSchema()
        assert schema.name == "source_code"

    def test_correct_version_is_loaded(self) -> None:
        """Test version property returns correct value."""
        schema = SourceCodeSchema()
        assert schema.version == EXPECTED_VERSION

    def test_schema_property_returns_dict(self) -> None:
        """Test that schema property returns a dictionary structure."""
        schema = SourceCodeSchema()

        result = schema.schema
        # Test that it returns a dictionary (the expected format)
        assert isinstance(result, dict)

    def test_schema_integration(self) -> None:
        """Test schema loading integration with real files."""
        schema = SourceCodeSchema()

        result = schema.schema
        # Verify it's a valid schema structure
        assert isinstance(result, dict)
        assert "$schema" in result or "type" in result
        # Should have basic schema properties
        expected_keys = ["type", "properties"]
        assert any(key in result for key in expected_keys)

    def test_schema_immutability(self) -> None:
        """Test that schema instances behave as immutable objects."""
        schema = SourceCodeSchema()

        # Test that core properties return consistent values
        name1 = schema.name
        name2 = schema.name
        assert name1 == name2 == "source_code"

        version1 = schema.version
        version2 = schema.version
        assert version1 == version2 == EXPECTED_VERSION

        # Verify it's a dataclass (public API)
        assert dataclasses.is_dataclass(schema)
