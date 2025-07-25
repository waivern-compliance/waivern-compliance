import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema

from .schema import WctSchema


@dataclass(slots=True)
class Message:
    """Payload between WCT components.

    This class represents a message that can be passed between different
    components of the WCT system, such as connectors and plugins.
    """

    id: str
    """Unique identifier for the message."""

    content: dict[str, Any]
    """Content of the message, typically in WCF schema format."""

    schema: WctSchema[Any] | None = None
    """Optional schema to validate the content against. If not provided, the
    default schema of the current plugin will be used."""

    context: dict[str, Any] | None = None
    """Optional context for the message, which can include additional metadata
    such as user information, timestamps, or other relevant data."""

    schema_validated: bool = False

    def validate(self):
        """Validate the message against its schema.

        Validates the message content against the WCT schema using JSON schema validation.
        Updates the schema_validated flag based on validation results.

        Returns:
            Message: Self for method chaining

        Raises:
            MessageValidationError: If validation fails with detailed error information
        """
        if not self.schema:
            self.schema_validated = False
            raise MessageValidationError("No schema provided for validation")

        if not self.content:
            self.schema_validated = False
            raise MessageValidationError("No content provided for validation")

        try:
            # Load the JSON schema file for validation
            schema = self._load_json_schema(self.schema.name)

            # Validate the content against the JSON schema
            jsonschema.validate(self.content, schema)

            # Mark as validated if successful
            self.schema_validated = True
            return self

        except jsonschema.ValidationError as e:
            self.schema_validated = False
            raise MessageValidationError(
                f"Schema validation failed for schema '{self.schema.name}': {e.message}"
            ) from e
        except FileNotFoundError as e:
            self.schema_validated = False
            raise MessageValidationError(
                f"Schema file not found for '{self.schema.name}': {e}"
            ) from e
        except Exception as e:
            self.schema_validated = False
            raise MessageValidationError(f"Validation error: {e}") from e

    def _load_json_schema(self, schema_name: str) -> dict[str, Any]:
        """Load JSON schema from file.

        Args:
            schema_name: Name of the schema to load

        Returns:
            The JSON schema as a dictionary

        Raises:
            FileNotFoundError: If schema file doesn't exist
        """
        # Try multiple potential locations for schema files
        schema_paths = [
            Path("src/wct/schemas") / f"{schema_name}.json",
            Path("./src/wct/schemas") / f"{schema_name}.json",
            Path(__file__).parent / "schemas" / f"{schema_name}.json",
        ]

        for schema_path in schema_paths:
            if schema_path.exists():
                with open(schema_path, "r") as f:
                    return json.load(f)

        raise FileNotFoundError(
            f"Schema file for '{schema_name}' not found in any of: {schema_paths}"
        )


class MessageValidationError(Exception):
    """Raised when message validation fails."""

    pass
