"""Integration tests for JSON Schema with real WCT runbooks.

These tests focus on areas not covered by existing unit tests:
- Validating actual sample runbooks against JSON Schema
- Testing JSON Schema + Pydantic validation consistency
- Using bundled schema files for validation

Following integration testing principles:
- Use real sample runbook files from runbooks/samples/
- Test end-to-end schema workflows
- Validate compatibility between validation systems
- Use British English spelling throughout ✔️
"""

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from wct.runbook import RunbookLoader
from wct.schemas.runbook import RunbookSchemaGenerator


class TestSchemaIntegration:
    """Integration tests for JSON Schema validation with real WCT runbooks."""

    def test_sample_runbooks_validate_with_json_schema(self) -> None:
        """Test that all actual sample runbooks validate with JSON Schema."""
        schema = RunbookSchemaGenerator.generate_schema()

        # Get all sample runbooks
        sample_dir = Path("runbooks/samples")
        sample_files = list(sample_dir.glob("*.yaml"))

        # Ensure we have samples to test
        assert len(sample_files) >= 2, (
            f"Expected at least 2 sample files, found {len(sample_files)}"
        )

        for runbook_path in sample_files:
            with open(runbook_path, encoding="utf-8") as f:
                runbook_data = yaml.safe_load(f)

            # Should validate successfully with JSON Schema
            jsonschema.validate(instance=runbook_data, schema=schema)

    def test_json_schema_pydantic_validation_consistency(self) -> None:
        """Test that JSON Schema and Pydantic validation agree on sample runbooks."""
        schema = RunbookSchemaGenerator.generate_schema()
        sample_dir = Path("runbooks/samples")

        for runbook_path in sample_dir.glob("*.yaml"):
            with open(runbook_path, encoding="utf-8") as f:
                runbook_data = yaml.safe_load(f)

            # Both validation methods should succeed
            pydantic_runbook = RunbookLoader.load(runbook_path)  # Pydantic validation
            jsonschema.validate(
                instance=runbook_data, schema=schema
            )  # JSON Schema validation

            # Verify core data consistency between validation methods
            assert pydantic_runbook.name == runbook_data["name"]
            assert pydantic_runbook.description == runbook_data["description"]
            assert len(pydantic_runbook.execution) == len(runbook_data["execution"])

    def test_bundled_schema_file_validates_samples(self) -> None:
        """Test that the bundled schema file validates sample runbooks."""
        bundled_path = RunbookSchemaGenerator.get_schema_path()

        # Skip test if bundled schema doesn't exist
        if not bundled_path.exists():
            pytest.skip(
                "Bundled schema file doesn't exist. Run 'wct generate-schema' first."
            )

        # Load the existing bundled schema file
        with open(bundled_path, encoding="utf-8") as f:
            bundled_schema = json.load(f)

        # Test all sample runbooks against bundled schema
        sample_dir = Path("runbooks/samples")
        for runbook_path in sample_dir.glob("*.yaml"):
            with open(runbook_path, encoding="utf-8") as f:
                runbook_data = yaml.safe_load(f)

            # Should validate with bundled schema
            jsonschema.validate(instance=runbook_data, schema=bundled_schema)

    def test_template_runbook_validates_with_schema(self) -> None:
        """Test that the bundled template runbook validates with generated schema."""
        schema = RunbookSchemaGenerator.generate_schema()
        template_path = Path(
            "src/wct/schemas/json_schemas/runbook/1.0.0/runbook.template.yaml"
        )

        with open(template_path, encoding="utf-8") as f:
            template_data = yaml.safe_load(f)

        # Template should validate successfully
        jsonschema.validate(instance=template_data, schema=schema)
