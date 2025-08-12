"""Tests for RunbookSchema."""

import dataclasses

from wct.schemas.runbook import RunbookSchema

# Version constant for easy maintenance
EXPECTED_VERSION = "1.0.0"


class TestRunbookSchema:
    """Tests for RunbookSchema."""

    def test_init_creates_working_schema(self) -> None:
        """Test initialization creates a working schema instance."""
        schema = RunbookSchema()
        # Test that the schema instance has the expected public interface
        assert hasattr(schema, "name")
        assert hasattr(schema, "version")
        assert hasattr(schema, "schema")
        # Test that the properties are actually accessible
        assert isinstance(schema.name, str)
        assert isinstance(schema.version, str)

    def test_name_property(self) -> None:
        """Test name property returns correct value."""
        schema = RunbookSchema()
        assert schema.name == "runbook"

    def test_correct_version_is_loaded(self) -> None:
        """Test version property returns correct value."""
        schema = RunbookSchema()
        assert schema.version == EXPECTED_VERSION

    def test_schema_property_returns_dict(self) -> None:
        """Test that schema property returns a dictionary structure."""
        schema = RunbookSchema()

        result = schema.schema
        # Test that it returns a dictionary (the expected format)
        assert isinstance(result, dict)

    def test_schema_integration(self) -> None:
        """Test schema loading integration with real files."""
        schema = RunbookSchema()

        result = schema.schema
        # Verify it's a valid schema structure
        assert isinstance(result, dict)
        assert "$schema" in result or "type" in result
        # Should have basic schema properties
        expected_keys = ["type", "properties"]
        assert any(key in result for key in expected_keys)

    def test_schema_immutability(self) -> None:
        """Test that schema instances behave as immutable objects."""
        schema = RunbookSchema()

        # Test that core properties return consistent values
        name1 = schema.name
        name2 = schema.name
        assert name1 == name2 == "runbook"

        version1 = schema.version
        version2 = schema.version
        assert version1 == version2 == EXPECTED_VERSION

        # Verify it's a dataclass (public API)
        assert dataclasses.is_dataclass(schema)

    def test_schema_structure_validation(self) -> None:
        """Test that the runbook schema has expected validation structure."""
        schema = RunbookSchema()
        result = schema.schema

        # Should be a JSON Schema
        assert result.get("$schema") == "http://json-schema.org/draft-07/schema#"
        assert result.get("type") == "object"
        assert result.get("title") == "WCT Runbook Schema"

        # Should have required top-level properties
        properties = result.get("properties", {})
        expected_properties = [
            "name",
            "description",
            "connectors",
            "analysers",
            "execution",
        ]
        for prop in expected_properties:
            assert prop in properties, f"Missing required property: {prop}"

        # Should have required fields specified
        required = result.get("required", [])
        for prop in expected_properties:
            assert prop in required, f"Property {prop} should be required"

    def test_schema_connector_validation_structure(self) -> None:
        """Test that connector validation structure is correct."""
        schema = RunbookSchema()
        result = schema.schema

        connectors_schema = result["properties"]["connectors"]
        assert connectors_schema["type"] == "array"
        assert connectors_schema["minItems"] == 1

        connector_item_schema = connectors_schema["items"]
        assert connector_item_schema["type"] == "object"

        # Check connector required fields
        connector_properties = connector_item_schema["properties"]
        expected_connector_fields = ["name", "type", "properties"]
        for field in expected_connector_fields:
            assert field in connector_properties

        connector_required = connector_item_schema["required"]
        for field in expected_connector_fields:
            assert field in connector_required

    def test_schema_analyser_validation_structure(self) -> None:
        """Test that analyser validation structure is correct."""
        schema = RunbookSchema()
        result = schema.schema

        analysers_schema = result["properties"]["analysers"]
        assert analysers_schema["type"] == "array"
        assert analysers_schema["minItems"] == 1

        analyser_item_schema = analysers_schema["items"]
        assert analyser_item_schema["type"] == "object"

        # Check analyser required fields
        analyser_properties = analyser_item_schema["properties"]
        expected_analyser_fields = ["name", "type", "properties"]
        for field in expected_analyser_fields:
            assert field in analyser_properties

        # Check metadata is optional
        assert "metadata" in analyser_properties

        analyser_required = analyser_item_schema["required"]
        for field in expected_analyser_fields:
            assert field in analyser_required

        # metadata should be optional
        assert "metadata" not in analyser_required

    def test_schema_execution_validation_structure(self) -> None:
        """Test that execution validation structure is correct."""
        schema = RunbookSchema()
        result = schema.schema

        execution_schema = result["properties"]["execution"]
        assert execution_schema["type"] == "array"
        assert execution_schema["minItems"] == 1

        execution_item_schema = execution_schema["items"]
        assert execution_item_schema["type"] == "object"

        # Check execution step required fields
        execution_properties = execution_item_schema["properties"]
        expected_execution_fields = [
            "connector",
            "analyser",
            "input_schema_name",
            "output_schema_name",
        ]
        for field in expected_execution_fields:
            assert field in execution_properties

        # Check context is optional
        assert "context" in execution_properties

        execution_required = execution_item_schema["required"]
        for field in expected_execution_fields:
            assert field in execution_required

        # context should be optional
        assert "context" not in execution_required

    def test_schema_name_pattern_validation(self) -> None:
        """Test that name fields have proper pattern validation."""
        schema = RunbookSchema()
        result = schema.schema

        # Check connector name pattern
        connector_name_schema = result["properties"]["connectors"]["items"][
            "properties"
        ]["name"]
        assert "pattern" in connector_name_schema
        assert connector_name_schema["pattern"] == "^[a-zA-Z0-9._-]+$"

        # Check analyser name pattern
        analyser_name_schema = result["properties"]["analysers"]["items"]["properties"][
            "name"
        ]
        assert "pattern" in analyser_name_schema
        assert analyser_name_schema["pattern"] == "^[a-zA-Z0-9._-]+$"

        # Check execution step patterns
        execution_item = result["properties"]["execution"]["items"]["properties"]
        for field in ["connector", "analyser"]:
            assert "pattern" in execution_item[field]
            assert execution_item[field]["pattern"] == "^[a-zA-Z0-9._-]+$"

    def test_schema_no_additional_properties(self) -> None:
        """Test that schema prevents additional properties where expected."""
        schema = RunbookSchema()
        result = schema.schema

        # Root level should not allow additional properties
        assert result.get("additionalProperties") is False

        # Connector items should not allow additional properties
        connector_item_schema = result["properties"]["connectors"]["items"]
        assert connector_item_schema.get("additionalProperties") is False

        # Analyser items should not allow additional properties
        analyser_item_schema = result["properties"]["analysers"]["items"]
        assert analyser_item_schema.get("additionalProperties") is False

        # Execution items should not allow additional properties
        execution_item_schema = result["properties"]["execution"]["items"]
        assert execution_item_schema.get("additionalProperties") is False
