"""Tests for DataSubjectFindingSchema."""

from wct.schemas.data_subject_finding import DataSubjectFindingSchema

# Version constant for easy maintenance
EXPECTED_VERSION = "1.0.0"


class TestDataSubjectFindingSchema:
    """Tests for DataSubjectFindingSchema."""

    def test_init_creates_working_schema(self) -> None:
        """Test initialization creates a working schema instance."""
        schema = DataSubjectFindingSchema()
        # Test that the schema instance has the expected public interface
        assert hasattr(schema, "name")
        assert hasattr(schema, "version")
        assert hasattr(schema, "schema")
        # Test that the properties are actually accessible
        assert isinstance(schema.name, str)
        assert isinstance(schema.version, str)

    def test_name_and_version_properties(self) -> None:
        """Test name and version properties return correct values."""
        schema = DataSubjectFindingSchema()
        assert schema.name == "data_subject_finding"
        assert schema.version == EXPECTED_VERSION

    def test_schema_loading_integration(self) -> None:
        """Test schema loading integration with real files."""
        schema = DataSubjectFindingSchema()

        result = schema.schema
        # Verify it's a valid schema structure
        assert isinstance(result, dict)
        assert "$schema" in result or "type" in result
        # Should have basic schema properties
        expected_keys = ["type", "properties"]
        assert any(key in result for key in expected_keys)
