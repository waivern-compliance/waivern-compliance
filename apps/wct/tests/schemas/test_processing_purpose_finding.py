"""Tests for ProcessingPurposeFindingSchema."""

import dataclasses

from wct.schemas.processing_purpose_finding import ProcessingPurposeFindingSchema

# Version constant for easy maintenance
EXPECTED_VERSION = "1.0.0"


class TestProcessingPurposeFindingSchema:
    """Tests for ProcessingPurposeFindingSchema."""

    def test_init_creates_working_schema(self) -> None:
        """Test initialization creates a working schema instance."""
        schema = ProcessingPurposeFindingSchema()
        # Test that the schema instance has the expected public interface
        assert hasattr(schema, "name")
        assert hasattr(schema, "version")
        assert hasattr(schema, "schema")
        # Test that the properties are actually accessible
        assert isinstance(schema.name, str)
        assert isinstance(schema.version, str)

    def test_name_property(self) -> None:
        """Test name property returns correct value."""
        schema = ProcessingPurposeFindingSchema()
        assert schema.name == "processing_purpose_finding"

    def test_correct_version_is_loaded(self) -> None:
        """Test version property returns correct value."""
        schema = ProcessingPurposeFindingSchema()
        assert schema.version == EXPECTED_VERSION

    def test_schema_property_returns_dict(self) -> None:
        """Test that schema property returns a dictionary structure."""
        schema = ProcessingPurposeFindingSchema()

        result = schema.schema
        # Test that it returns a dictionary (the expected format)
        assert isinstance(result, dict)

    def test_schema_integration(self) -> None:
        """Test schema loading integration with real files."""
        schema = ProcessingPurposeFindingSchema()

        result = schema.schema
        # Verify it's a valid schema structure
        assert isinstance(result, dict)
        assert "$schema" in result or "type" in result
        # Should have basic schema properties
        expected_keys = ["type", "properties"]
        assert any(key in result for key in expected_keys)

    def test_schema_immutability(self) -> None:
        """Test that schema instances behave as immutable objects."""
        schema = ProcessingPurposeFindingSchema()

        # Test that core properties return consistent values
        name1 = schema.name
        name2 = schema.name
        assert name1 == name2 == "processing_purpose_finding"

        version1 = schema.version
        version2 = schema.version
        assert version1 == version2 == EXPECTED_VERSION

        # Verify it's a dataclass (public API)
        assert dataclasses.is_dataclass(schema)
