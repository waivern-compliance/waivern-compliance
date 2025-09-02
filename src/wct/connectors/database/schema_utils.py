"""Database schema validation and transformation utilities."""

from wct.connectors.base import ConnectorConfigError
from wct.schemas import Schema


class DatabaseSchemaUtils:
    """Utilities for database schema validation and transformation."""

    @staticmethod
    def validate_output_schema(
        schema: Schema | None, supported_schemas: tuple[Schema, ...]
    ) -> Schema:
        """Validate the output schema.

        Args:
            schema: Schema to validate
            supported_schemas: List of supported schemas

        Returns:
            The validated schema

        Raises:
            ConnectorConfigError: If schema is invalid or unsupported

        """
        # Validate no duplicate schema types in supported schemas
        supported_schema_types = tuple(type(s) for s in supported_schemas)
        if len(supported_schema_types) != len(set(supported_schema_types)):
            raise ConnectorConfigError(
                "Duplicate schema types not allowed in supported schemas"
            )

        # Handle None schema case - use first supported schema as default
        if schema is None:
            if not supported_schemas:
                raise ConnectorConfigError("No supported schemas available")
            return supported_schemas[0]

        # Validate schema is supported
        if type(schema) not in supported_schema_types:
            supported_schema_names = [s.name for s in supported_schemas]
            raise ConnectorConfigError(
                f"Unsupported output schema: {schema.name}. "
                f"Supported schemas: {supported_schema_names}"
            )

        return schema
