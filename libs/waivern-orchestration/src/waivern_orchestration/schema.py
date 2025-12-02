"""JSON Schema generation for Runbook models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from waivern_orchestration.models import Runbook


class RunbookSchemaGenerator:
    """Generates and manages JSON schemas for runbook validation."""

    SCHEMA_VERSION = "1.0.0"

    @classmethod
    def generate_schema(cls) -> dict[str, Any]:
        """Generate JSON schema from Pydantic Runbook model.

        Returns:
            Dictionary containing the generated JSON schema.

        """
        schema = Runbook.model_json_schema()

        # Create ordered dictionary with schema metadata at the beginning
        ordered_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "version": cls.SCHEMA_VERSION,
            **schema,
        }

        # Update the title and description
        ordered_schema["title"] = "Waivern Runbook"
        ordered_schema["description"] = (
            "Waivern Compliance Framework runbook configuration schema"
        )

        return ordered_schema

    @classmethod
    def save_schema(cls, output_path: Path) -> None:
        """Save generated schema to file.

        Args:
            output_path: Path where the schema file should be saved.

        Raises:
            OSError: If the file cannot be written.

        """
        schema = cls.generate_schema()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)
