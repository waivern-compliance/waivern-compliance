"""Utility functions for Waivern Compliance Framework."""

from datetime import UTC, datetime
from typing import Any

from waivern_core.errors import ConnectorConfigError
from waivern_core.message import Message
from waivern_core.schemas import Schema


def update_analyses_chain(
    input_message: Message, analyser_name: str
) -> list[dict[str, Any]]:
    """Extract existing analysis chain and add new entry with correct order.

    This function works with generic dictionary representations of chain entries,
    making it independent of specific data models. Applications can define
    their own typed models and convert to/from dicts as needed.

    Args:
        input_message: Input message that may contain existing analysis metadata
        analyser_name: Name of the current analyser to add to the chain

    Returns:
        Updated analysis chain as a list of dictionaries with the new analyser entry.
        Each dict should contain at minimum: {"order": int, "analyser": str}

    """
    existing_chain: list[dict[str, Any]] = []

    # Extract existing analysis chain from input message if present
    if hasattr(input_message.content, "get") and input_message.content.get(
        "analysis_metadata"
    ):
        metadata = input_message.content["analysis_metadata"]
        if "analyses_chain" in metadata:
            existing_chain = list(metadata["analyses_chain"])

    # Calculate next order number
    next_order = (
        max(entry["order"] for entry in existing_chain) + 1 if existing_chain else 1
    )

    # Create new entry and extend chain
    new_entry: dict[str, Any] = {
        "order": next_order,
        "analyser": analyser_name,
        "execution_timestamp": datetime.now(UTC),
    }
    return existing_chain + [new_entry]


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
