"""Tests for ProcessingPurposeIndicatorSchema."""

from waivern_core.schemas import Schema

# Version constant for easy maintenance
EXPECTED_VERSION = "1.0.0"


class TestProcessingPurposeIndicatorSchema:
    """Tests for ProcessingPurposeIndicatorSchema."""

    def test_init_creates_working_schema(self) -> None:
        """Test initialization creates a working schema instance."""
        schema = Schema("processing_purpose_indicator", "1.0.0")
        # Test that the schema instance has the expected public interface
        assert hasattr(schema, "name")
        assert hasattr(schema, "version")
        assert hasattr(schema, "schema")
        # Test that the properties are actually accessible
        assert isinstance(schema.name, str)
        assert isinstance(schema.version, str)

    def test_name_property(self) -> None:
        """Test name property returns correct value."""
        schema = Schema("processing_purpose_indicator", "1.0.0")
        assert schema.name == "processing_purpose_indicator"

    def test_correct_version_is_loaded(self) -> None:
        """Test version property returns correct value."""
        schema = Schema("processing_purpose_indicator", "1.0.0")
        assert schema.version == EXPECTED_VERSION

    def test_schema_property_returns_dict(self) -> None:
        """Test that schema property returns a dictionary structure."""
        schema = Schema("processing_purpose_indicator", "1.0.0")

        result = schema.schema
        # Test that it returns a dictionary (the expected format)
        assert isinstance(result, dict)

    def test_schema_integration(self) -> None:
        """Test schema loading integration with real files."""
        schema = Schema("processing_purpose_indicator", "1.0.0")

        result = schema.schema
        # Verify it's a valid schema structure
        assert isinstance(result, dict)
        assert "$schema" in result or "type" in result
        # Should have basic schema properties
        expected_keys = ["type", "properties"]
        assert any(key in result for key in expected_keys)

    def test_schema_immutability(self) -> None:
        """Test that schema instances behave as immutable objects."""
        schema = Schema("processing_purpose_indicator", "1.0.0")

        # Test that core properties return consistent values
        name1 = schema.name
        name2 = schema.name
        assert name1 == name2 == "processing_purpose_indicator"

        version1 = schema.version
        version2 = schema.version
        assert version1 == version2 == EXPECTED_VERSION
