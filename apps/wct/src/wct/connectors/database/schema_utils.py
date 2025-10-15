"""Database schema validation and transformation utilities."""

from waivern_core.errors import ConnectorConfigError
from waivern_core.schemas import Schema


class DatabaseSchemaUtils:
    """Utilities for database schema validation and transformation."""

    @staticmethod
    def validate_output_schema(
        schema: Schema | None, supported_schemas: list[Schema]
    ) -> Schema:
        """Validate the output schema.

        Args:
            schema: Schema to validate
            supported_schemas: List of supported schemas (duplicates will be removed while preserving order)

        Returns:
            The validated schema

        Raises:
            ConnectorConfigError: If schema is invalid or unsupported

        """
        # Remove duplicates while preserving order using dict.fromkeys()
        unique_schemas = list(dict.fromkeys(supported_schemas))

        # Handle None schema case - use first unique schema as default
        if schema is None:
            if not unique_schemas:
                raise ConnectorConfigError("No supported schemas available")
            return unique_schemas[0]

        # Validate schema is supported (uses type-based __eq__ comparison)
        if schema not in unique_schemas:
            supported_schema_names = [s.name for s in unique_schemas]
            raise ConnectorConfigError(
                f"Unsupported output schema: {schema.name}. "
                f"Supported schemas: {supported_schema_names}"
            )

        return schema
