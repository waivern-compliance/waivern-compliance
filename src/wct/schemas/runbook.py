"""JSON Schema generation for WCT runbooks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from wct.runbook import Runbook


class RunbookSchemaGenerator:
    """Generates and manages JSON schemas for runbook validation."""

    SCHEMA_VERSION = "1.0.0"

    @classmethod
    def generate_schema(cls) -> dict[str, Any]:
        """Generate JSON schema from Pydantic Runbook model.

        Returns:
            Dictionary containing the generated JSON schema

        """
        schema = Runbook.model_json_schema()

        # Create new ordered dictionary with WCT-specific metadata at the beginning
        ordered_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "version": cls.SCHEMA_VERSION,
            **schema,
        }

        # Update the title and description
        ordered_schema["title"] = "WCT Runbook"
        ordered_schema["description"] = (
            "Waivern Compliance Tool runbook configuration schema"
        )

        return ordered_schema

    @classmethod
    def save_schema(cls, output_path: Path) -> None:
        """Save generated schema to file.

        Args:
            output_path: Path where the schema file should be saved

        Raises:
            OSError: If the file cannot be written

        """
        schema = cls.generate_schema()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)

    @classmethod
    def get_schema_path(cls) -> Path:
        """Get path to bundled schema file.

        Returns:
            Path to the bundled runbook schema file

        """
        # Get the path relative to this module
        current_dir = Path(__file__).parent
        return (
            current_dir
            / "json_schemas"
            / "runbook"
            / cls.SCHEMA_VERSION
            / "runbook.json"
        )

    @classmethod
    def get_schema_url(cls) -> str:
        """Get URL for the schema (for potential future remote hosting).

        Returns:
            URL string for the schema

        """
        return f"https://raw.githubusercontent.com/waivern-compliance/waivern-compliance/main/src/wct/schemas/json_schemas/runbook/{cls.SCHEMA_VERSION}/runbook.json"
