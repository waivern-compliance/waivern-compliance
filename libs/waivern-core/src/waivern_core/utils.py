"""Utility functions for Waivern Compliance Framework."""

from waivern_core.errors import ConnectorConfigError
from waivern_core.schemas import Schema


def validate_output_schema(schema: Schema, supported_schemas: list[Schema]) -> None:
    """Validate that the output schema is supported by the connector.

    This is a shared utility for connectors to validate that a requested
    output schema is in their list of supported schemas.

    Uses Schema's __eq__ method which compares both name and version,
    ensuring that requesting v2.0.0 when only v1.0.0 is supported will fail.

    Args:
        schema: The schema to validate
        supported_schemas: List of schemas supported by the connector

    Raises:
        ConnectorConfigError: If schema is not in supported_schemas

    """
    if schema not in supported_schemas:
        supported_list = [f"{s.name} {s.version}" for s in supported_schemas]
        raise ConnectorConfigError(
            f"Unsupported output schema: {schema.name} {schema.version}. "
            f"Supported schemas: {supported_list}"
        )
