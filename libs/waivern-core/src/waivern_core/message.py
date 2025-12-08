"""Message handling for Waivern Compliance Framework components.

This module provides:
- Message: dataclass for payloads between framework components
- MessageValidationError: exception for message validation failures
"""

from dataclasses import dataclass
from typing import Any, Self

import jsonschema

from waivern_core.errors import MessageValidationError
from waivern_core.schemas import Schema, SchemaLoadError


@dataclass(slots=True)
class Message:
    """Payload between Waivern Compliance Framework components.

    This class represents a message that can be passed between different
    components of the framework, such as connectors and analysers.
    """

    id: str
    """Unique identifier for the message."""

    content: dict[str, Any]
    """Content of the message, typically in WCF schema format."""

    schema: Schema
    """Schema to validate the content against."""

    context: dict[str, Any] | None = None
    """Optional context for the message, which can include additional metadata
    such as user information, timestamps, or other relevant data."""

    schema_validated: bool = False

    def validate(self) -> Self:
        """Validate the message against its schema.

        Validates the message content against the WCF schema using JSON schema validation.
        Updates the schema_validated flag based on validation results.

        Returns:
            Message: Self for method chaining

        Raises:
            MessageValidationError: If validation fails with detailed error information

        """
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
