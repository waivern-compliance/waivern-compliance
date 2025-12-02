"""Tests for RunbookSchemaGenerator."""

import json
from pathlib import Path

from waivern_orchestration import RunbookSchemaGenerator


class TestRunbookSchemaGenerator:
    """Tests for RunbookSchemaGenerator schema generation."""

    def test_generated_schema_is_valid_json_schema(self) -> None:
        """Generated schema conforms to JSON Schema draft-07 specification."""
        schema = RunbookSchemaGenerator.generate_schema()

        assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"

    def test_generated_schema_identifies_as_waivern_runbook(self) -> None:
        """Generated schema identifies itself as Waivern Runbook schema."""
        schema = RunbookSchemaGenerator.generate_schema()

        assert "Waivern" in schema["title"]
        assert "Runbook" in schema["title"]

    def test_generated_schema_includes_version(self) -> None:
        """Generated schema includes version for compatibility tracking."""
        schema = RunbookSchemaGenerator.generate_schema()

        assert "version" in schema
        assert isinstance(schema["version"], str)

    def test_generated_schema_has_description(self) -> None:
        """Generated schema provides description for documentation."""
        schema = RunbookSchemaGenerator.generate_schema()

        assert "description" in schema
        assert len(schema["description"]) > 0

    def test_save_schema_creates_valid_json_file(self, tmp_path: Path) -> None:
        """Saved schema file can be loaded as valid JSON."""
        output_path = tmp_path / "runbook_schema.json"

        RunbookSchemaGenerator.save_schema(output_path)

        assert output_path.exists()
        with open(output_path, encoding="utf-8") as f:
            loaded = json.load(f)
        assert isinstance(loaded, dict)

    def test_save_schema_creates_parent_directories(self, tmp_path: Path) -> None:
        """Save creates parent directories if they do not exist."""
        nested_path = tmp_path / "nested" / "dirs" / "schema.json"

        RunbookSchemaGenerator.save_schema(nested_path)

        assert nested_path.exists()

    def test_saved_schema_matches_generated_schema(self, tmp_path: Path) -> None:
        """Saved schema content matches what generate_schema returns."""
        output_path = tmp_path / "schema.json"

        RunbookSchemaGenerator.save_schema(output_path)

        with open(output_path, encoding="utf-8") as f:
            saved = json.load(f)
        generated = RunbookSchemaGenerator.generate_schema()

        assert saved == generated
