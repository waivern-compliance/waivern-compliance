"""Tests for RunbookSchemaGenerator.

These tests focus on the RunbookSchemaGenerator class functionality, ensuring proper
JSON schema generation from Pydantic models and correct metadata handling.

Following black-box testing principles:
- Focus on public API only - test the public methods of RunbookSchemaGenerator
- Test behaviour and contracts, not implementation details
- Use realistic test scenarios with temporary resources
- Test edge cases and error conditions through public interfaces
- Avoid mocking internal dependencies
- Use British English spelling throughout ✔️
"""

import json
from pathlib import Path

from wct.schemas.runbook import RunbookSchemaGenerator


class TestRunbookSchemaGenerator:
    """Test RunbookSchemaGenerator functionality."""

    def test_generate_schema_returns_valid_structure(self) -> None:
        """Test that generate_schema returns valid JSON Schema structure."""
        schema = RunbookSchemaGenerator.generate_schema()

        # Verify basic JSON Schema structure
        assert isinstance(schema, dict)
        assert "$schema" in schema
        assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
        assert "properties" in schema
        assert "required" in schema
        assert "type" in schema
        assert schema["type"] == "object"

    def test_generate_schema_includes_wct_metadata(self) -> None:
        """Test that generate_schema includes WCT-specific metadata."""
        schema = RunbookSchemaGenerator.generate_schema()

        # Verify WCT-specific metadata
        assert schema["title"] == "WCT Runbook"
        assert (
            "Waivern Compliance Tool runbook configuration schema"
            in schema["description"]
        )
        assert schema["version"] == RunbookSchemaGenerator.SCHEMA_VERSION
        assert schema["version"] == "1.0.0"

    def test_generate_schema_includes_execution_step_fields(self) -> None:
        """Test that ExecutionStep definition includes mandatory name and description fields."""
        schema = RunbookSchemaGenerator.generate_schema()

        # Navigate to ExecutionStep definition
        assert "$defs" in schema
        assert "ExecutionStep" in schema["$defs"]

        execution_step = schema["$defs"]["ExecutionStep"]
        properties = execution_step["properties"]

        # Verify name field with constraints
        assert "name" in properties
        name_field = properties["name"]
        assert name_field["type"] == "string"
        assert name_field["minLength"] == 1
        assert (
            "Human-readable name for this execution step" in name_field["description"]
        )

        # Verify description field
        assert "description" in properties
        description_field = properties["description"]
        assert description_field["type"] == "string"
        assert "can be empty" in description_field["description"]

        # Verify both are required
        assert "name" in execution_step["required"]
        assert "description" in execution_step["required"]

    def test_generate_schema_includes_all_runbook_components(self) -> None:
        """Test that schema includes all expected runbook components."""
        schema = RunbookSchemaGenerator.generate_schema()

        properties = schema["properties"]
        required_fields = schema["required"]

        # Verify main runbook fields
        expected_properties = [
            "name",
            "description",
            "connectors",
            "analysers",
            "execution",
        ]
        for prop in expected_properties:
            assert prop in properties, f"Missing property: {prop}"
            assert prop in required_fields, f"Property not required: {prop}"

    def test_generate_schema_includes_component_definitions(self) -> None:
        """Test that schema includes definitions for all component types."""
        schema = RunbookSchemaGenerator.generate_schema()

        # Verify component definitions exist
        defs = schema["$defs"]
        expected_defs = ["ConnectorConfig", "AnalyserConfig", "ExecutionStep"]
        for def_name in expected_defs:
            assert def_name in defs, f"Missing definition: {def_name}"

    def test_schema_is_json_serialisable(self) -> None:
        """Test that generated schema can be serialised to JSON."""
        schema = RunbookSchemaGenerator.generate_schema()

        # Should not raise an exception
        json_string = json.dumps(schema, indent=2, ensure_ascii=False)

        # Should be able to deserialise back
        deserialised = json.loads(json_string)
        assert deserialised == schema

    def test_get_schema_path_returns_versioned_path(self) -> None:
        """Test that get_schema_path returns correctly versioned path structure."""
        schema_path = RunbookSchemaGenerator.get_schema_path()

        # Verify path structure
        assert isinstance(schema_path, Path)
        path_parts = schema_path.parts
        assert "json_schemas" in path_parts
        assert "runbook" in path_parts
        assert RunbookSchemaGenerator.SCHEMA_VERSION in path_parts
        assert schema_path.name == "runbook.json"

    def test_get_schema_url_returns_github_url(self) -> None:
        """Test that get_schema_url returns correctly formatted GitHub URL."""
        schema_url = RunbookSchemaGenerator.get_schema_url()

        # Verify URL structure
        assert isinstance(schema_url, str)
        assert schema_url.startswith("https://raw.githubusercontent.com")
        assert "waivern-compliance/waivern-compliance" in schema_url
        assert RunbookSchemaGenerator.SCHEMA_VERSION in schema_url
        assert schema_url.endswith("/runbook.json")

    def test_schema_version_consistency(self) -> None:
        """Test that schema version is consistent across all methods."""
        schema = RunbookSchemaGenerator.generate_schema()
        schema_path = RunbookSchemaGenerator.get_schema_path()
        schema_url = RunbookSchemaGenerator.get_schema_url()

        version = RunbookSchemaGenerator.SCHEMA_VERSION

        # Verify version consistency
        assert schema["version"] == version
        assert version in str(schema_path)
        assert version in schema_url

    def test_save_schema_basic_functionality(self, tmp_path: Path) -> None:
        """Test basic save_schema functionality without duplicating CLI tests."""
        output_path = tmp_path / "basic_test.json"

        # This is the core unit test - does save_schema work at all?
        RunbookSchemaGenerator.save_schema(output_path)

        # Verify basic file creation and content
        assert output_path.exists()

        with open(output_path, encoding="utf-8") as f:
            saved_schema = json.load(f)

        # Compare with directly generated schema
        expected_schema = RunbookSchemaGenerator.generate_schema()
        assert saved_schema == expected_schema

    def test_schema_enforces_name_patterns(self) -> None:
        """Test that schema enforces proper name patterns for components."""
        schema = RunbookSchemaGenerator.generate_schema()

        # Check name pattern constraints for connectors
        connector_name = schema["$defs"]["ConnectorConfig"]["properties"]["name"]
        assert connector_name["minLength"] == 1
        assert "pattern" in connector_name
        assert "^[a-zA-Z0-9._-]+$" == connector_name["pattern"]

        # Check name pattern constraints for analysers
        analyser_name = schema["$defs"]["AnalyserConfig"]["properties"]["name"]
        assert analyser_name["minLength"] == 1
        assert "pattern" in analyser_name
        assert "^[a-zA-Z0-9._-]+$" == analyser_name["pattern"]

    def test_schema_defines_array_constraints(self) -> None:
        """Test that schema properly defines array constraints for lists."""
        schema = RunbookSchemaGenerator.generate_schema()

        properties = schema["properties"]

        # Check connectors array constraints
        connectors = properties["connectors"]
        assert connectors["type"] == "array"
        assert connectors["minItems"] == 1
        assert "$ref" in connectors["items"]

        # Check analysers array constraints
        analysers = properties["analysers"]
        assert analysers["type"] == "array"
        assert analysers["minItems"] == 1
        assert "$ref" in analysers["items"]

        # Check execution array constraints
        execution = properties["execution"]
        assert execution["type"] == "array"
        assert execution["minItems"] == 1
        assert "$ref" in execution["items"]
