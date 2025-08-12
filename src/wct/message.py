"""Message handling for WCT components.

This module provides:
- Message: dataclass for payloads between WCT components
- MessageValidationError: exception for message validation failures
"""

from dataclasses import dataclass
from typing import Any

import jsonschema
from typing_extensions import Self

from .schemas.base import Schema, SchemaLoadError


@dataclass(slots=True)
class Message:
    """Payload between WCT components.

    This class represents a message that can be passed between different
    components of the WCT system, such as connectors and analysers.
    """

    id: str
    """Unique identifier for the message."""

    content: dict[str, Any]
    """Content of the message, typically in WCF schema format."""

    schema: Schema | None = None
    """Schema to validate the content against. If not provided, the
    default schema of the current analyser will be used."""

    context: dict[str, Any] | None = None
    """Optional context for the message, which can include additional metadata
    such as user information, timestamps, or other relevant data."""

    schema_validated: bool = False

    def validate(self) -> Self:
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
            # Get the JSON schema definition from the schema object
            schema_definition = self.schema.schema

            # Validate the content against the JSON schema
            jsonschema.validate(self.content, schema_definition)

            # Mark as validated if successful
            self.schema_validated = True
            return self

        except jsonschema.ValidationError as e:
            self.schema_validated = False
            raise MessageValidationError(
                f"Schema validation failed for schema '{self.schema.name}': {e.message}"
            ) from e
        except (FileNotFoundError, SchemaLoadError) as e:
            self.schema_validated = False
            raise MessageValidationError(
                f"Schema loading failed for '{self.schema.name}': {e}"
            ) from e
        except Exception as e:
            self.schema_validated = False
            raise MessageValidationError(f"Validation error: {e}") from e


class MessageValidationError(Exception):
    """Raised when message validation fails."""

    pass
